from __future__ import annotations

import asyncio
import json
import logging
import ssl
from typing import Any

from asyncio_mqtt import Client, MqttError
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..analytics.rules import AnalyticsEngine
from ..config import get_settings
from ..db import get_sessionmaker
from ..models import Insight, Node, NodeStatus, Site, TelemetryRaw
from ..schemas.telemetry import TelemetryPayload

logger = logging.getLogger(__name__)


class TelemetryIngestService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.analytics = AnalyticsEngine()
        self.sessionmaker = get_sessionmaker()

    async def _persist_telemetry(self, session: AsyncSession, payload: TelemetryPayload) -> None:
        site_stmt = (
            insert(Site)
            .values(
                site_id=payload.site_id,
                name=payload.site_id,
                org_id=payload.org_id,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(site_stmt)

        node_stmt = (
            insert(Node)
            .values(
                node_id=payload.node_id,
                name=payload.node_id,
                org_id=payload.org_id,
                site_id=payload.site_id,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(node_stmt)

        telemetry_stmt = (
            insert(TelemetryRaw)
            .values(
                org_id=payload.org_id,
                site_id=payload.site_id,
                node_id=payload.node_id,
                ts=payload.ts,
                soil_moisture=payload.sensors.soil_moisture,
                soil_temp_c=payload.sensors.soil_temp_c,
                air_temp_c=payload.sensors.air_temp_c,
                humidity=payload.sensors.humidity,
                light_lux=payload.sensors.light_lux,
                vbat=payload.sensors.vbat,
                rssi=payload.rssi,
                fw_version=payload.fw_version,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(telemetry_stmt)

        health = "ok"
        if payload.sensors.vbat is not None and payload.sensors.vbat < 3.6:
            health = "low_battery"

        status_stmt = (
            insert(NodeStatus)
            .values(
                org_id=payload.org_id,
                site_id=payload.site_id,
                node_id=payload.node_id,
                last_seen=payload.ts,
                battery_v=payload.sensors.vbat,
                fw_version=payload.fw_version,
                health=health,
            )
            .on_conflict_do_update(
                index_elements=[NodeStatus.node_id],
                set_={
                    "last_seen": payload.ts,
                    "battery_v": payload.sensors.vbat,
                    "fw_version": payload.fw_version,
                    "health": health,
                },
            )
        )
        await session.execute(status_stmt)

        insights = self.analytics.evaluate(payload)
        for event in insights:
            insight_stmt = insert(Insight).values(
                org_id=payload.org_id,
                site_id=payload.site_id,
                node_id=payload.node_id,
                ts=payload.ts,
                type=event.type,
                payload=event.payload,
            )
            await session.execute(insight_stmt)

    async def _handle_message(self, topic: str, data: bytes) -> None:
        try:
            payload_dict: dict[str, Any] = json.loads(data)
            payload = TelemetryPayload.model_validate(payload_dict)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Failed to parse telemetry: %s", exc)
            return

        org_allow = set(filter(None, self.settings.service_org_allowlist))
        if org_allow and payload.org_id not in org_allow:
            logger.debug("Skipping telemetry for org %s", payload.org_id)
            return

        async with self.sessionmaker() as session:
            await self._persist_telemetry(session, payload)
            await session.commit()

    async def run(self) -> None:
        backoff = 1
        while True:
            try:
                await self._consume()
            except MqttError as exc:
                logger.error("MQTT error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except Exception:
                logger.exception("Unexpected error in ingest loop")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            else:
                backoff = 1

    async def _consume(self) -> None:
        settings = self.settings
        connect_kwargs = {}
        if settings.mqtt_username:
            connect_kwargs["username"] = settings.mqtt_username
        if settings.mqtt_password:
            connect_kwargs["password"] = settings.mqtt_password
        if settings.mqtt_tls_enabled:
            connect_kwargs["tls_context"] = ssl.create_default_context()

        async with Client(settings.mqtt_broker_host, settings.mqtt_broker_port, **connect_kwargs) as client:
            telemetry_filter = settings.telemetry_topic_filter
            async with client.filtered_messages(telemetry_filter) as messages:
                await client.subscribe(telemetry_filter)
                async for message in messages:
                    await self._handle_message(message.topic, message.payload)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    service = TelemetryIngestService()
    asyncio.run(service.run())


if __name__ == "__main__":
    run()
