from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any

from asyncio_mqtt import Client
from redis.asyncio import Redis
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import structlog

from .config import IngestorSettings, get_settings
from .models import telemetry_table

logger = structlog.get_logger()


def serialise_message(message: dict[str, Any]) -> str:
    return json.dumps(message, separators=(",", ":"))


def build_tls_context(settings: IngestorSettings) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=settings.mqtt.tls_ca_path)
    if settings.mqtt.client_cert_path and settings.mqtt.client_key_path:
        context.load_cert_chain(settings.mqtt.client_cert_path, settings.mqtt.client_key_path)
    context.check_hostname = False
    return context


async def handle_message(payload: str, redis: Redis, engine: AsyncEngine, settings: IngestorSettings) -> None:
    message = json.loads(payload)
    async with engine.begin() as conn:
        await conn.execute(
            insert(telemetry_table).values(
                device_id=message["deviceId"],
                soil_moisture=message["soilMoisture"],
                soil_temp_c=message["soilTempC"],
                ambient_temp_c=message["ambientTempC"],
                ambient_humidity=message["ambientHumidity"],
                light_lux=message["lightLux"],
                battery_voltage=message["batteryVoltage"],
            )
        )
    await redis.publish(settings.redis.telemetry_channel, serialise_message(message))
    logger.info("ingested", device=message["deviceId"])


async def run_async() -> None:
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    redis = Redis.from_url(settings.redis.url)
    engine = create_async_engine(settings.database.dsn)
    tls_context = build_tls_context(settings)

    async with Client(
        settings.mqtt.host,
        port=settings.mqtt.port,
        username=settings.mqtt.username,
        password=settings.mqtt.password,
        tls_context=tls_context,
    ) as client:
        async with client.filtered_messages(settings.mqtt.topic) as messages:
            await client.subscribe(settings.mqtt.topic)
            async for message in messages:
                payload = message.payload.decode()
                try:
                    await handle_message(payload, redis, engine, settings)
                except Exception as exc:  # noqa: BLE001
                    logger.error("failed_to_process", error=str(exc))


def run() -> None:
    asyncio.run(run_async())
