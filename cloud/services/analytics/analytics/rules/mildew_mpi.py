from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..alert_manager import create_alert, create_recommendation, resolve_alerts_for_rule
from ..models import blocks, nodes, telemetry_readings, vineyards

logger = structlog.get_logger()

_RULE_HIGH = "mildew_high"
_RULE_MODERATE = "mildew_moderate"
_COOLDOWN_HOURS = 6

# MPI thresholds
_TEMP_MIN = 15.0       # °C — lower bound for mildew-favourable temp
_TEMP_MAX = 27.0       # °C — upper bound
_RH_HIGH = 78.0        # % — high MPI humidity threshold
_RH_MODERATE = 70.0    # % — moderate MPI humidity threshold
_WET_HOURS_HIGH = 2    # hours of leaf wetness for high MPI
_WET_HOURS_MODERATE = 1  # hours for moderate MPI

# Each telemetry reading is treated as ~30 minutes of data (proxy for wet_hours count).
# wet_hours = count(readings where leaf_wetness_pct > 0) * 0.5
_READING_INTERVAL_H = 0.5


async def run(engine: AsyncEngine) -> None:
    """Evaluate Mildew Pressure Index (MPI) for precision_plus nodes only.

    Uses the last 6 hours of leaf wetness, temperature, and humidity data.
    MPI tiers:
    - High:     wet_hours >= 2, 15 <= avg_temp <= 27, avg_RH >= 78  → critical
    - Moderate: wet_hours >= 1, 15 <= avg_temp <= 27, avg_RH >= 70  → warning
    """
    window = datetime.now(tz=timezone.utc) - timedelta(hours=6)

    query = (
        select(
            nodes.c.id.label("node_id"),
            nodes.c.device_id,
            nodes.c.tier,
            blocks.c.id.label("block_id"),
            blocks.c.name.label("block_name"),
            vineyards.c.id.label("vineyard_id"),
            # Count readings where leaf wetness > 0 (proxy for wet hours at 30-min intervals)
            func.count(
                telemetry_readings.c.id
            ).filter(
                telemetry_readings.c.leaf_wetness_pct > 0
            ).label("wet_reading_count"),
            func.avg(telemetry_readings.c.ambient_temp_c).label("avg_temp"),
            func.avg(telemetry_readings.c.ambient_humidity).label("avg_humidity"),
            func.count(telemetry_readings.c.id).label("total_readings"),
        )
        .select_from(
            telemetry_readings
            .join(nodes, nodes.c.device_id == telemetry_readings.c.device_id)
            .join(blocks, blocks.c.id == nodes.c.block_id)
            .join(vineyards, vineyards.c.id == blocks.c.vineyard_id)
        )
        .where(
            and_(
                telemetry_readings.c.recorded_at >= window,
                # Only precision_plus nodes have leaf wetness sensors
                nodes.c.tier == "precision_plus",
                telemetry_readings.c.leaf_wetness_pct.isnot(None),
                telemetry_readings.c.ambient_temp_c.isnot(None),
                telemetry_readings.c.ambient_humidity.isnot(None),
            )
        )
        .group_by(
            nodes.c.id,
            nodes.c.device_id,
            nodes.c.tier,
            blocks.c.id,
            blocks.c.name,
            vineyards.c.id,
        )
    )

    async with engine.begin() as conn:
        rows = (await conn.execute(query)).mappings().all()

        high_node_ids: list[str] = []
        moderate_node_ids: list[str] = []

        for row in rows:
            # This filter is already in the query but double-check for safety
            if row["tier"] != "precision_plus":
                continue

            node_id = str(row["node_id"])
            block_id = str(row["block_id"])
            vineyard_id = str(row["vineyard_id"])
            block_name = row["block_name"]
            avg_temp = row["avg_temp"]
            avg_humidity = row["avg_humidity"]

            # Convert wet reading count to hours using 30-min interval proxy
            wet_hours = (row["wet_reading_count"] or 0) * _READING_INTERVAL_H

            if avg_temp is None or avg_humidity is None:
                continue

            temp_in_range = _TEMP_MIN <= avg_temp <= _TEMP_MAX

            is_high_mpi = (
                wet_hours >= _WET_HOURS_HIGH
                and temp_in_range
                and avg_humidity >= _RH_HIGH
            )
            is_moderate_mpi = (
                not is_high_mpi
                and wet_hours >= _WET_HOURS_MODERATE
                and temp_in_range
                and avg_humidity >= _RH_MODERATE
            )

            if is_high_mpi:
                high_node_ids.append(node_id)
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_HIGH,
                    severity="critical",
                    title=f"High Mildew Pressure — {block_name}",
                    message=(
                        f"Leaf wetness {wet_hours:.1f}h+, temp {avg_temp:.1f}°C, "
                        f"RH {avg_humidity:.0f}% — high downy/powdery mildew risk."
                    ),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Apply preventative mildew treatment in {block_name} within "
                        "48 hours. Scout for early infection signs."
                    ),
                    priority=1,
                )
                logger.info(
                    "mildew_high_alert",
                    block=block_name,
                    wet_hours=wet_hours,
                    avg_temp=round(avg_temp, 1),
                    avg_humidity=round(avg_humidity, 0),
                )

            elif is_moderate_mpi:
                moderate_node_ids.append(node_id)
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_MODERATE,
                    severity="warning",
                    title=f"Moderate Mildew Risk — {block_name}",
                    message=(
                        f"Leaf wetness {wet_hours:.1f}h, temp {avg_temp:.1f}°C, "
                        f"RH {avg_humidity:.0f}% — moderate mildew pressure."
                    ),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Increased mildew pressure in {block_name}. "
                        "Inspect canopy and schedule protective spray."
                    ),
                    priority=2,
                )
                logger.info(
                    "mildew_moderate_alert",
                    block=block_name,
                    wet_hours=wet_hours,
                    avg_temp=round(avg_temp, 1),
                    avg_humidity=round(avg_humidity, 0),
                )

        await resolve_alerts_for_rule(conn, _RULE_HIGH, high_node_ids)
        await resolve_alerts_for_rule(conn, _RULE_MODERATE, moderate_node_ids)

    logger.info("mildew_mpi_rule_complete", rows_evaluated=len(rows))
