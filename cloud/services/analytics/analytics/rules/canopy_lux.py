from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..alert_manager import create_alert, create_recommendation, resolve_alerts_for_rule
from ..models import blocks, nodes, telemetry_readings, vineyards

logger = structlog.get_logger()

_RULE_KEY = "canopy_density"
_COOLDOWN_HOURS = 24
_LUX_RATIO_THRESHOLD = 0.70   # alert if max_lux < 70% of reference


async def run(engine: AsyncEngine) -> None:
    """Compare peak light readings for each block against its reference_lux_peak.

    Only evaluates readings taken during peak sun hours (10:00–14:00 UTC) over the
    last 24 hours. Blocks with no reference value are skipped.
    """
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=24)

    # Max lux per node during peak hours
    query = (
        select(
            nodes.c.id.label("node_id"),
            nodes.c.device_id,
            blocks.c.id.label("block_id"),
            blocks.c.name.label("block_name"),
            blocks.c.reference_lux_peak,
            vineyards.c.id.label("vineyard_id"),
            func.max(telemetry_readings.c.light_lux).label("max_lux"),
        )
        .select_from(
            telemetry_readings
            .join(nodes, nodes.c.device_id == telemetry_readings.c.device_id)
            .join(blocks, blocks.c.id == nodes.c.block_id)
            .join(vineyards, vineyards.c.id == blocks.c.vineyard_id)
        )
        .where(
            telemetry_readings.c.recorded_at >= window_start,
            telemetry_readings.c.light_lux.isnot(None),
            # Peak sun hours: hour >= 10 AND hour < 14 UTC
            func.extract("hour", telemetry_readings.c.recorded_at) >= 10,
            func.extract("hour", telemetry_readings.c.recorded_at) < 14,
        )
        .group_by(
            nodes.c.id,
            nodes.c.device_id,
            blocks.c.id,
            blocks.c.name,
            blocks.c.reference_lux_peak,
            vineyards.c.id,
        )
    )

    async with engine.begin() as conn:
        rows = (await conn.execute(query)).mappings().all()

        triggering_node_ids: list[str] = []

        for row in rows:
            ref = row["reference_lux_peak"]
            if ref is None or ref <= 0:
                # No reference value — cannot evaluate
                continue

            node_id = str(row["node_id"])
            block_id = str(row["block_id"])
            vineyard_id = str(row["vineyard_id"])
            block_name = row["block_name"]
            max_lux = row["max_lux"]

            if max_lux < _LUX_RATIO_THRESHOLD * ref:
                pct = (max_lux / ref) * 100.0
                triggering_node_ids.append(node_id)
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_KEY,
                    severity="info",
                    title=f"Canopy Density — {block_name}",
                    message=(
                        f"Peak lux {max_lux:.0f} is {pct:.0f}% of reference "
                        f"({ref:.0f}). Canopy may be limiting light."
                    ),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Scout {block_name} for canopy density. "
                        "Consider targeted leaf removal around fruit zone."
                    ),
                    priority=3,
                )
                logger.info(
                    "canopy_density_alert",
                    block=block_name,
                    max_lux=round(max_lux, 0),
                    reference_lux=round(ref, 0),
                    pct=round(pct, 1),
                )

        await resolve_alerts_for_rule(conn, _RULE_KEY, triggering_node_ids)

    logger.info("canopy_lux_rule_complete", rows_evaluated=len(rows))
