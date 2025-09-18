from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import structlog

from .config import AnalyticsSettings, get_settings
from .models import analytics_signals, telemetry_readings

logger = structlog.get_logger()


async def check_moisture_trends(engine: AsyncEngine) -> None:
    window = datetime.utcnow() - timedelta(hours=6)
    query: Select = (
        select(
            telemetry_readings.c.device_id,
            func.avg(telemetry_readings.c.soil_moisture).label("avg_moisture"),
        )
        .where(telemetry_readings.c.recorded_at >= window)
        .group_by(telemetry_readings.c.device_id)
        .having(func.avg(telemetry_readings.c.soil_moisture) < 30)
    )
    async with engine.begin() as conn:
        results = (await conn.execute(query)).all()
        for device_id, avg_moisture in results:
            await conn.execute(
                analytics_signals.insert().values(
                    device_id=device_id,
                    signal_type="low_moisture",
                    severity="warning",
                    description=f"Average soil moisture {avg_moisture:.1f}% over 6h",
                )
            )
    if results:
        logger.info("generated_signals", count=len(results))


async def run_periodic_jobs(settings: AnalyticsSettings) -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    engine = create_async_engine(settings.database.dsn)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_moisture_trends, "interval", seconds=settings.polling_interval_seconds, args=[engine])
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    finally:
        await engine.dispose()
        scheduler.shutdown()


def run() -> None:
    settings = get_settings()
    asyncio.run(run_periodic_jobs(settings))
