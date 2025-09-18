import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Deque, Optional
from uuid import UUID

from pydantic import BaseModel, BaseSettings, Field
from redis import asyncio as aioredis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analytics")


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    batch_interval_seconds: int = Field(300, env="BATCH_INTERVAL_SECONDS")
    low_battery_threshold: float = Field(20, env="LOW_BATTERY_THRESHOLD")
    low_moisture_threshold: float = Field(0.3, env="LOW_MOISTURE_THRESHOLD")
    frozen_variance_threshold: float = Field(0.02, env="FROZEN_VARIANCE_THRESHOLD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class TelemetryEvent(BaseModel):
    event: str = "telemetry"
    org_id: UUID
    node_id: UUID
    timestamp: datetime
    battery_level: Optional[float]
    temperature: Optional[float]
    moisture: Optional[float]


@dataclass
class TemperatureWindow:
    samples: Deque[float]
    timestamps: Deque[datetime]


class AnalyticsWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings.database_url, pool_pre_ping=True)
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self.temp_windows: dict[UUID, TemperatureWindow] = defaultdict(
            lambda: TemperatureWindow(deque(maxlen=10), deque(maxlen=10))
        )

    async def start(self) -> None:
        await asyncio.gather(self.consume_stream(), self.run_batch_loop())

    async def consume_stream(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("org:*:live")
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0.05)
                    continue
                try:
                    data = json.loads(message["data"])
                    event = TelemetryEvent(**data)
                except Exception:  # pragma: no cover - defensive
                    logger.exception("Failed to parse telemetry event: %s", message)
                    continue
                if event.event != "telemetry":
                    continue
                await self.handle_rules(event)
        finally:
            await pubsub.close()

    async def handle_rules(self, event: TelemetryEvent) -> None:
        insights: list[tuple[str, str, str, dict]] = []
        if event.battery_level is not None and event.battery_level < self.settings.low_battery_threshold:
            insights.append(
                (
                    "battery_low",
                    "warning",
                    f"Node {event.node_id} battery at {event.battery_level:.1f}%",
                    {"battery_level": event.battery_level},
                )
            )

        if event.moisture is not None and event.moisture < self.settings.low_moisture_threshold:
            insights.append(
                (
                    "moisture_low",
                    "warning",
                    f"Node {event.node_id} moisture below threshold ({event.moisture:.2f})",
                    {"moisture": event.moisture},
                )
            )

        if event.temperature is not None:
            window = self.temp_windows[event.node_id]
            window.samples.append(event.temperature)
            window.timestamps.append(event.timestamp)
            if len(window.samples) >= 5:
                if max(window.samples) - min(window.samples) <= self.settings.frozen_variance_threshold:
                    duration = (window.timestamps[-1] - window.timestamps[0]).total_seconds()
                    if duration >= 900:
                        insights.append(
                            (
                                "sensor_frozen",
                                "info",
                                "Temperature readings unchanged for 15 minutes",
                                {"temperature": list(window.samples)},
                            )
                        )
                        window.samples.clear()
                        window.timestamps.clear()

        for insight in insights:
            await self.save_insight(event, *insight)

    async def save_insight(
        self,
        event: TelemetryEvent,
        insight_type: str,
        severity: str,
        message: str,
        metadata: dict,
    ) -> None:
        def _write():
            with Session(self.engine) as session:
                session.execute(
                    text(
                        """
                        INSERT INTO insights (org_id, node_id, insight_type, severity, message, metadata)
                        VALUES (:org_id, :node_id, :insight_type, :severity, :message, :metadata)
                        """
                    ),
                    {
                        "org_id": str(event.org_id),
                        "node_id": str(event.node_id),
                        "insight_type": insight_type,
                        "severity": severity,
                        "message": message,
                        "metadata": json.dumps(metadata),
                    },
                )
                session.commit()

        await asyncio.to_thread(_write)
        payload = {
            "event": "insight",
            "org_id": str(event.org_id),
            "node_id": str(event.node_id),
            "type": insight_type,
            "severity": severity,
            "message": message,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.redis.publish(f"org:{event.org_id}:live", json.dumps(payload, default=str))

    async def run_batch_loop(self) -> None:
        while True:
            try:
                await self.run_batch_job()
            except Exception:  # pragma: no cover - defensive
                logger.exception("Batch job failed")
            await asyncio.sleep(self.settings.batch_interval_seconds)

    async def run_batch_job(self) -> None:
        logger.info("Running batch analytics job")
        start = datetime.utcnow() - timedelta(hours=24)

        def _fetch():
            with Session(self.engine) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT node_id, reading_time, payload
                        FROM telemetry_raw
                        WHERE reading_time >= :start
                        ORDER BY node_id, reading_time
                        """
                    ),
                    {"start": start},
                )
                data: dict[UUID, list[tuple[datetime, float]]] = defaultdict(list)
                for row in rows.mappings():
                    payload = json.loads(row["payload"])
                    moisture = payload.get("moisture")
                    if moisture is not None:
                        data[UUID(row["node_id"])].append((row["reading_time"], float(moisture)))
                return data

        data = await asyncio.to_thread(_fetch)
        for node_id, samples in data.items():
            if len(samples) < 5:
                continue
            values = [value for _, value in samples]
            avg = mean(values)
            deviation = pstdev(values)
            latest_time, latest_value = samples[-1]
            if deviation > 0:
                z_score = (latest_value - avg) / deviation
                if z_score <= -1.5:
                    await self._maybe_emit_batch_insight(
                        node_id,
                        latest_time,
                        "moisture_zscore",
                        "info",
                        f"Moisture z-score low ({z_score:.2f}). Consider irrigation.",
                        {"z_score": z_score, "latest": latest_value, "average": avg},
                    )
            if latest_value < self.settings.low_moisture_threshold:
                await self._maybe_emit_batch_insight(
                    node_id,
                    latest_time,
                    "irrigation_advice",
                    "info",
                    "Moisture trending low. Schedule irrigation window soon.",
                    {"latest": latest_value, "average": avg},
                )

    async def _maybe_emit_batch_insight(
        self,
        node_id: UUID,
        timestamp: datetime,
        insight_type: str,
        severity: str,
        message: str,
        metadata: dict,
    ) -> None:
        def _check_and_insert():
            with Session(self.engine) as session:
                exists = session.execute(
                    text(
                        """
                        SELECT 1 FROM insights
                        WHERE node_id = :node_id AND insight_type = :insight_type
                          AND created_at >= :window_start
                        LIMIT 1
                        """
                    ),
                    {
                        "node_id": str(node_id),
                        "insight_type": insight_type,
                        "window_start": timestamp - timedelta(hours=1),
                    },
                ).first()
                if exists:
                    return None
                session.execute(
                    text(
                        """
                        INSERT INTO insights (org_id, node_id, insight_type, severity, message, metadata, created_at)
                        VALUES ((SELECT org_id FROM nodes WHERE id = :node_id), :node_id, :insight_type, :severity, :message, :metadata, :created_at)
                        """
                    ),
                    {
                        "node_id": str(node_id),
                        "insight_type": insight_type,
                        "severity": severity,
                        "message": message,
                        "metadata": json.dumps(metadata),
                        "created_at": timestamp,
                    },
                )
                session.commit()
                org_id = session.execute(
                    text("SELECT org_id FROM nodes WHERE id = :node_id"),
                    {"node_id": str(node_id)},
                ).scalar()
                return org_id

        org_id = await asyncio.to_thread(_check_and_insert)
        if org_id:
            payload = {
                "event": "insight",
                "org_id": str(org_id),
                "node_id": str(node_id),
                "type": insight_type,
                "severity": severity,
                "message": message,
                "metadata": metadata,
                "created_at": timestamp.isoformat(),
            }
            await self.redis.publish(f"org:{org_id}:live", json.dumps(payload, default=str))


async def main() -> None:
    settings = Settings()
    worker = AnalyticsWorker(settings)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
