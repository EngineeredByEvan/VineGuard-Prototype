from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from ..alert_manager import create_alert, create_recommendation
from ..models import alerts, gdd_accumulation, telemetry_readings, nodes, blocks, vineyards

logger = structlog.get_logger()

_BASE_TEMP_C = 10.0   # standard grapevine base temperature

# Milestone definitions: (gdd_threshold, rule_name_suffix, severity, title, recommendation_text)
_MILESTONES: list[tuple[float, str, str, str, str]] = [
    (
        147,
        "bud_break",
        "info",
        "Bud Break Approaching",
        "Begin basal shoot removal and position young shoots.",
    ),
    (
        350,
        "shoot_development",
        "info",
        "Shoot Development",
        "Scout for early-season pests. Deploy pheromone traps.",
    ),
    (
        550,
        "bloom",
        "warning",
        "Bloom",
        "Monitor for botrytis at bloom. Avoid overhead irrigation.",
    ),
    (
        810,
        "veraison_approach",
        "info",
        "Veraison Approach",
        "Sample for sugar development. Adjust irrigation to moderate stress.",
    ),
    (
        1100,
        "ripening",
        "info",
        "Ripening",
        "Begin pre-harvest scouting. Assess sugar/acid balance.",
    ),
    (
        1620,
        "harvest_window",
        "warning",
        "Harvest Window",
        "Initiate final harvest readiness assessment.",
    ),
]


async def _get_previous_season_total(
    conn: Any, vineyard_id: str, today: date
) -> float:
    """Sum all gdd_daily entries from March 1 of the current year up to yesterday."""
    season_start = date(today.year, 3, 1)
    stmt = select(func.coalesce(func.sum(gdd_accumulation.c.gdd_daily), 0.0)).where(
        and_(
            gdd_accumulation.c.vineyard_id == vineyard_id,
            gdd_accumulation.c.date >= season_start,
            gdd_accumulation.c.date < today,
        )
    )
    result = await conn.execute(stmt)
    return float(result.scalar())


async def _milestone_already_alerted(
    conn: Any, vineyard_id: str, rule_key: str
) -> bool:
    """Return True if an active (or recently resolved) milestone alert exists within cooldown."""
    stmt = select(alerts).where(
        and_(
            alerts.c.vineyard_id == vineyard_id,
            alerts.c.rule_key == rule_key,
        )
    ).limit(1)
    row = (await conn.execute(stmt)).first()
    return row is not None


async def run(engine: AsyncEngine) -> None:
    """Compute daily GDD for each vineyard and check phenological milestones.

    GDD formula: max(0, (daily_max + daily_min) / 2 - BASE_TEMP_C)
    Season total: sum of gdd_daily from March 1 to today.
    Milestones fire once per 7-day cooldown window (stored as an active alert).
    """
    today = datetime.now(tz=timezone.utc).date()

    # Aggregate today's temperature extremes per vineyard
    query = (
        select(
            vineyards.c.id.label("vineyard_id"),
            vineyards.c.name.label("vineyard_name"),
            func.max(telemetry_readings.c.ambient_temp_c).label("daily_max"),
            func.min(telemetry_readings.c.ambient_temp_c).label("daily_min"),
        )
        .select_from(
            telemetry_readings
            .join(nodes, nodes.c.device_id == telemetry_readings.c.device_id)
            .join(blocks, blocks.c.id == nodes.c.block_id)
            .join(vineyards, vineyards.c.id == blocks.c.vineyard_id)
        )
        .where(
            func.date(telemetry_readings.c.recorded_at) == today,
            telemetry_readings.c.ambient_temp_c.isnot(None),
        )
        .group_by(vineyards.c.id, vineyards.c.name)
    )

    async with engine.begin() as conn:
        rows = (await conn.execute(query)).mappings().all()

        for row in rows:
            vineyard_id = str(row["vineyard_id"])
            vineyard_name = row["vineyard_name"]
            daily_max = row["daily_max"]
            daily_min = row["daily_min"]

            gdd_daily = max(0.0, (daily_max + daily_min) / 2.0 - _BASE_TEMP_C)

            # Pull the running season total up to yesterday, then add today
            previous_total = await _get_previous_season_total(conn, vineyard_id, today)
            season_total = previous_total + gdd_daily

            # Upsert into gdd_accumulation (conflict on vineyard_id + date)
            stmt = (
                pg_insert(gdd_accumulation)
                .values(
                    vineyard_id=vineyard_id,
                    date=today,
                    gdd_daily=gdd_daily,
                    gdd_season_total=season_total,
                )
                .on_conflict_do_update(
                    index_elements=["vineyard_id", "date"],
                    set_={
                        "gdd_daily": gdd_daily,
                        "gdd_season_total": season_total,
                    },
                )
            )
            await conn.execute(stmt)

            logger.info(
                "gdd_computed",
                vineyard=vineyard_name,
                gdd_daily=round(gdd_daily, 2),
                season_total=round(season_total, 2),
            )

            # Check milestones — fire alert if season total crossed the threshold
            # and no existing alert for that milestone exists (7-day cooldown).
            for threshold, name_suffix, severity, milestone_title, rec_text in _MILESTONES:
                # Only fire when we have crossed the milestone this season
                if season_total < threshold:
                    continue
                if previous_total >= threshold:
                    # Already crossed before today — no new crossing
                    continue

                rule_key = f"gdd_milestone_{name_suffix}"
                already = await _milestone_already_alerted(conn, vineyard_id, rule_key)
                if already:
                    continue

                alert_id = await create_alert(
                    conn,
                    node_id=None,
                    block_id=None,
                    vineyard_id=vineyard_id,
                    rule_key=rule_key,
                    severity=severity,
                    title=f"GDD Milestone: {milestone_title} — {vineyard_name}",
                    message=(
                        f"Season GDD reached {season_total:.0f} "
                        f"(milestone: {threshold} GDD — {milestone_title})."
                    ),
                    cooldown_hours=7 * 24,  # 7 days
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=None,
                    vineyard_id=vineyard_id,
                    action_text=rec_text,
                    priority=2,
                )
                logger.info(
                    "gdd_milestone_alert",
                    vineyard=vineyard_name,
                    milestone=milestone_title,
                    season_total=round(season_total, 2),
                )

    logger.info("gdd_rule_complete", vineyards_evaluated=len(rows))
