from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import structlog

from .config import AnalyticsSettings, get_settings
from .models import nodes
from .rules import canopy_lux, frost, gdd, mildew_mpi, moisture

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Node stale detection
# ---------------------------------------------------------------------------

async def check_stale_nodes(engine: AsyncEngine) -> None:
    """Update node status based on last_seen_at.

    - > 30 min without a heartbeat → 'stale'
    - > 2 hours without a heartbeat → 'inactive'
    """
    now = datetime.now(tz=timezone.utc)
    stale_cutoff = now - timedelta(minutes=30)
    inactive_cutoff = now - timedelta(hours=2)

    try:
        async with engine.begin() as conn:
            # Mark inactive first (more severe) so it takes precedence
            await conn.execute(
                update(nodes)
                .where(
                    nodes.c.last_seen_at < inactive_cutoff,
                    nodes.c.status != "inactive",
                )
                .values(status="inactive")
            )
            # Mark stale (nodes last seen between 30 min and 2 hours ago)
            await conn.execute(
                update(nodes)
                .where(
                    nodes.c.last_seen_at >= inactive_cutoff,
                    nodes.c.last_seen_at < stale_cutoff,
                    nodes.c.status != "stale",
                )
                .values(status="stale")
            )
        logger.debug("stale_node_check_complete")
    except Exception:
        logger.exception("stale_node_check_failed")


# ---------------------------------------------------------------------------
# Generic job wrapper
# ---------------------------------------------------------------------------

def _make_job(rule_name: str, rule_module):
    """Return an async callable that runs a rule module's run() and logs timing/errors."""

    async def _job(engine: AsyncEngine) -> None:
        t0 = time.monotonic()
        try:
            await rule_module.run(engine)
            elapsed = time.monotonic() - t0
            logger.info("rule_complete", rule=rule_name, elapsed_s=round(elapsed, 3))
        except Exception:
            elapsed = time.monotonic() - t0
            logger.exception("rule_failed", rule=rule_name, elapsed_s=round(elapsed, 3))

    # Give the wrapper a meaningful name for APScheduler's job list
    _job.__name__ = f"run_{rule_name}"
    return _job


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

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

    # Moisture — every 5 minutes
    scheduler.add_job(
        _make_job("moisture", moisture),
        "interval",
        minutes=5,
        args=[engine],
        id="moisture",
        name="Soil Moisture Rule",
    )

    # Frost — every 5 minutes (time-sensitive)
    scheduler.add_job(
        _make_job("frost", frost),
        "interval",
        minutes=5,
        args=[engine],
        id="frost",
        name="Frost Rule",
    )

    # Mildew MPI — every 10 minutes
    scheduler.add_job(
        _make_job("mildew_mpi", mildew_mpi),
        "interval",
        minutes=10,
        args=[engine],
        id="mildew_mpi",
        name="Mildew MPI Rule",
    )

    # Canopy Lux — every 60 minutes
    scheduler.add_job(
        _make_job("canopy_lux", canopy_lux),
        "interval",
        minutes=60,
        args=[engine],
        id="canopy_lux",
        name="Canopy Lux Rule",
    )

    # GDD — every 60 minutes (daily totals, polling is fine)
    scheduler.add_job(
        _make_job("gdd", gdd),
        "interval",
        minutes=60,
        args=[engine],
        id="gdd",
        name="GDD Accumulation Rule",
    )

    # Node stale detection — every 5 minutes
    scheduler.add_job(
        check_stale_nodes,
        "interval",
        minutes=5,
        args=[engine],
        id="stale_nodes",
        name="Node Stale Detection",
    )

    scheduler.start()
    logger.info(
        "scheduler_started",
        jobs=[job.id for job in scheduler.get_jobs()],
    )

    try:
        while True:
            await asyncio.sleep(60)
    finally:
        await engine.dispose()
        scheduler.shutdown()
        logger.info("scheduler_stopped")


def run() -> None:
    settings = get_settings()
    asyncio.run(run_periodic_jobs(settings))
