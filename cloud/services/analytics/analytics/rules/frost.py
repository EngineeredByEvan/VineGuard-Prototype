from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..alert_manager import create_alert, create_recommendation, resolve_alerts_for_rule
from ..models import blocks, nodes, telemetry_readings, vineyards

logger = structlog.get_logger()

_RULE_CRITICAL = "frost_critical"
_RULE_WARNING = "frost_warning"
_COOLDOWN_HOURS = 2

# Temperature thresholds (°C)
_TEMP_CRITICAL = 0.0   # below this → critical frost
_TEMP_WARNING = 3.0    # below this → warning frost risk


def _dewpoint(temp_c: float, rh: float) -> float:
    """Approximate dewpoint via the simple Magnus approximation.

    Formula: T - ((100 - RH) / 5)
    """
    return temp_c - ((100.0 - rh) / 5.0)


async def run(engine: AsyncEngine) -> None:
    """Evaluate frost risk for each node based on the latest reading within 2 hours.

    Tiers:
    - temp < 0°C  → critical: "Frost Alert"
    - 0°C <= temp < 3°C → warning: "Frost Risk"

    Dewpoint is computed for informational context but thresholds are temperature-based.
    Resolves frost alerts for nodes that have returned above 3°C.
    """
    window = datetime.now(tz=timezone.utc) - timedelta(hours=2)

    # Get the most recent reading per node within the last 2 hours.
    # We use a lateral-style approach by selecting the max recorded_at per node
    # then joining back to get the associated values.
    latest_ts_subq = (
        select(
            telemetry_readings.c.device_id,
            func.max(telemetry_readings.c.recorded_at).label("latest_at"),
        )
        .where(
            telemetry_readings.c.recorded_at >= window,
            telemetry_readings.c.ambient_temp_c.isnot(None),
        )
        .group_by(telemetry_readings.c.device_id)
        .subquery("latest_ts")
    )

    query = (
        select(
            nodes.c.id.label("node_id"),
            nodes.c.device_id,
            blocks.c.id.label("block_id"),
            blocks.c.name.label("block_name"),
            vineyards.c.id.label("vineyard_id"),
            telemetry_readings.c.ambient_temp_c,
            telemetry_readings.c.ambient_humidity,
        )
        .select_from(
            latest_ts_subq
            .join(
                telemetry_readings,
                (telemetry_readings.c.device_id == latest_ts_subq.c.device_id)
                & (telemetry_readings.c.recorded_at == latest_ts_subq.c.latest_at),
            )
            .join(nodes, nodes.c.device_id == telemetry_readings.c.device_id)
            .join(blocks, blocks.c.id == nodes.c.block_id)
            .join(vineyards, vineyards.c.id == blocks.c.vineyard_id)
        )
        .where(telemetry_readings.c.ambient_temp_c.isnot(None))
    )

    async with engine.begin() as conn:
        rows = (await conn.execute(query)).mappings().all()

        critical_node_ids: list[str] = []
        warning_node_ids: list[str] = []

        for row in rows:
            node_id = str(row["node_id"])
            block_id = str(row["block_id"])
            vineyard_id = str(row["vineyard_id"])
            block_name = row["block_name"]
            temp = row["ambient_temp_c"]
            rh = row["ambient_humidity"]

            # Compute dewpoint if humidity is available
            dewpoint = _dewpoint(temp, rh) if rh is not None else None

            if temp < _TEMP_CRITICAL:
                critical_node_ids.append(node_id)
                msg_parts = [f"Ambient temperature {temp:.1f}°C — active frost conditions."]
                if dewpoint is not None:
                    msg_parts.append(f"Dewpoint: {dewpoint:.1f}°C.")
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_CRITICAL,
                    severity="critical",
                    title=f"Frost Alert — {block_name}",
                    message=" ".join(msg_parts),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Activate frost protection in {block_name} immediately "
                        "(wind machines / sprinklers)."
                    ),
                    priority=1,
                )
                logger.info(
                    "frost_critical_alert",
                    block=block_name,
                    temp_c=round(temp, 1),
                    dewpoint_c=round(dewpoint, 1) if dewpoint is not None else None,
                )

            elif _TEMP_CRITICAL <= temp < _TEMP_WARNING:
                warning_node_ids.append(node_id)
                msg_parts = [f"Ambient temperature {temp:.1f}°C — frost risk."]
                if dewpoint is not None:
                    msg_parts.append(f"Dewpoint: {dewpoint:.1f}°C.")
                alert_id = await create_alert(
                    conn,
                    node_id=node_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    rule_key=_RULE_WARNING,
                    severity="warning",
                    title=f"Frost Risk — {block_name}",
                    message=" ".join(msg_parts),
                    cooldown_hours=_COOLDOWN_HOURS,
                )
                await create_recommendation(
                    conn,
                    alert_id=alert_id,
                    block_id=block_id,
                    vineyard_id=vineyard_id,
                    action_text=(
                        f"Monitor temperatures closely in {block_name}. "
                        "Prepare frost mitigation."
                    ),
                    priority=1,
                )
                logger.info(
                    "frost_warning_alert",
                    block=block_name,
                    temp_c=round(temp, 1),
                    dewpoint_c=round(dewpoint, 1) if dewpoint is not None else None,
                )

        # Resolve frost alerts for nodes that are back above 3°C
        # (i.e., nodes not in critical_node_ids and not in warning_node_ids)
        safe_node_ids = [
            str(row["node_id"])
            for row in rows
            if row["ambient_temp_c"] >= _TEMP_WARNING
        ]
        # We resolve by supplying all still-triggering IDs; the manager excludes those.
        await resolve_alerts_for_rule(conn, _RULE_CRITICAL, critical_node_ids)
        await resolve_alerts_for_rule(conn, _RULE_WARNING, warning_node_ids)

    logger.info("frost_rule_complete", rows_evaluated=len(rows))
