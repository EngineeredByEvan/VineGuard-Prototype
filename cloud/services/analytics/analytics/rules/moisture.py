from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..alert_manager import create_alert, create_recommendation, resolve_alerts_for_rule
from ..models import blocks, nodes, telemetry_readings, vineyards

logger = structlog.get_logger()

_RULE_DRY = "moisture_dry"
_RULE_WET = "moisture_wet"
_THRESHOLD_DRY = 15.0   # percent
_THRESHOLD_WET = 75.0   # percent
_COOLDOWN_HOURS = 4


async def run(engine: AsyncEngine) -> None:
    """Evaluate soil moisture thresholds for each node over the last 3 hours.

    Raises a critical alert for dry conditions (<15%) and a warning for waterlogging
    (>75%). Resolves alerts for nodes that are back within the normal range.
    """
    window = datetime.now(tz=timezone.utc) - timedelta(hours=3)

    query = (
        select(
            nodes.c.id.label("node_id"),
            nodes.c.device_id,
            blocks.c.id.label("block_id"),
            blocks.c.name.label("block_name"),
            vineyards.c.id.label("vineyard_id"),
            func.avg(telemetry_readings.c.soil_moisture).label("avg_moisture"),
        )
        .select_from(
            telemetry_readings
            .join(nodes, nodes.c.device_id == telemetry_readings.c.device_id)
            .join(blocks, blocks.c.id == nodes.c.block_id)
            .join(vineyards, vineyards.c.id == blocks.c.vineyard_id)
        )
        .where(
            telemetry_readings.c.recorded_at >= window,
            telemetry_readings.c.soil_moisture.isnot(None),
        )
        .group_by(
            nodes.c.id,
            nodes.c.device_id,
            blocks.c.id,
            blocks.c.name,
            vineyards.c.id,
        )
    )

    async with engine.begin() as conn:
        rows = (await conn.execute(query)).mappings().all()

        dry_node_ids: list[str] = []
        wet_node_ids: list[str] = []

        for row in rows:
            node_id = str(row["node_id"])
            block_id = str(row["block_id"])
            vineyard_id = str(row["vineyard_id"])
            block_name = row["block_name"]
            avg = row["avg_moisture"]

            if avg < _THRESHOLD_DRY:
                dry_node_ids.append(node_id)
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_DRY,
                    severity="critical",
                    title=f"Low Soil Moisture — {block_name}",
                    message=(
                        f"Average soil moisture {avg:.1f}% over 3h "
                        f"(threshold: {_THRESHOLD_DRY:.0f}%)"
                    ),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Irrigate {block_name} within the next 24 hours. "
                        "Target 25–35% volumetric water content."
                    ),
                    priority=1,
                )
                logger.info(
                    "moisture_dry_alert",
                    block=block_name,
                    avg_moisture=round(avg, 1),
                )

            elif avg > _THRESHOLD_WET:
                wet_node_ids.append(node_id)
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_WET,
                    severity="warning",
                    title=f"Excess Soil Moisture — {block_name}",
                    message=(
                        f"Average soil moisture {avg:.1f}% over 3h — waterlogging risk"
                    ),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=f"Check drainage in {block_name}. Delay irrigation.",
                    priority=2,
                )
                logger.info(
                    "moisture_wet_alert",
                    block=block_name,
                    avg_moisture=round(avg, 1),
                )

        # Resolve dry alerts for nodes no longer below threshold
        await resolve_alerts_for_rule(conn, _RULE_DRY, dry_node_ids)
        # Resolve wet alerts for nodes no longer above threshold
        await resolve_alerts_for_rule(conn, _RULE_WET, wet_node_ids)

    logger.info("moisture_rule_complete", rows_evaluated=len(rows))
