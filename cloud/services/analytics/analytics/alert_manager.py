from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select, update

from .models import alerts, recommendations


async def get_active_alert(
    conn: Any,
    rule_key: str,
    node_id: str | None,
    block_id: str | None,
) -> dict | None:
    """Return the existing active alert for this rule+node or rule+block combo.

    Precedence: if node_id is given, match on node_id; otherwise match on block_id.
    Only returns an alert whose cooldown_until is in the future (i.e. still cooling
    down) OR whose cooldown_until is NULL/past but still active — callers use this
    to suppress duplicate creation when cooldown_until > now().
    """
    conditions = [
        alerts.c.rule_key == rule_key,
        alerts.c.is_active.is_(True),
    ]

    if node_id is not None:
        conditions.append(alerts.c.node_id == node_id)
    elif block_id is not None:
        conditions.append(alerts.c.block_id == block_id)
    else:
        # vineyard-level or no scope — match purely on rule_key + active
        pass

    stmt = select(alerts).where(and_(*conditions)).limit(1)
    row = (await conn.execute(stmt)).mappings().first()
    return dict(row) if row is not None else None


async def create_alert(
    conn: Any,
    *,
    node_id: str | None,
    block_id: str | None,
    vineyard_id: str,
    rule_key: str,
    severity: str,
    title: str,
    message: str,
    cooldown_hours: int = 4,
) -> str:
    """Create a new alert and set cooldown_until = now() + cooldown_hours.

    Returns the UUID of the newly created alert as a string.
    Skips creation if an active alert already exists within its cooldown window.
    """
    now = datetime.now(tz=timezone.utc)
    cooldown_until = now + timedelta(hours=cooldown_hours)

    # Check for an existing active alert still within cooldown.
    existing = await get_active_alert(conn, rule_key, node_id, block_id)
    if existing is not None:
        cu = existing.get("cooldown_until")
        if cu is not None:
            # Make tz-aware if it came back naive from the DB driver
            if cu.tzinfo is None:
                cu = cu.replace(tzinfo=timezone.utc)
            if cu > now:
                # Still in cooldown — do not create a duplicate
                return str(existing["id"])

    result = await conn.execute(
        alerts.insert().values(
            node_id=node_id,
            block_id=block_id,
            vineyard_id=vineyard_id,
            rule_key=rule_key,
            severity=severity,
            title=title,
            message=message,
            is_active=True,
            triggered_at=now,
            resolved_at=None,
            cooldown_until=cooldown_until,
        ).returning(alerts.c.id)
    )
    row = result.first()
    return str(row[0])


async def resolve_alerts_for_rule(
    conn: Any,
    rule_key: str,
    still_triggering_node_ids: list[str],
) -> None:
    """Resolve active alerts for rule_key where node_id is NOT in still_triggering_node_ids.

    Sets is_active=False and resolved_at=now() for matching rows.
    """
    now = datetime.now(tz=timezone.utc)

    conditions = [
        alerts.c.rule_key == rule_key,
        alerts.c.is_active.is_(True),
    ]

    if still_triggering_node_ids:
        conditions.append(alerts.c.node_id.notin_(still_triggering_node_ids))

    stmt = (
        update(alerts)
        .where(and_(*conditions))
        .values(is_active=False, resolved_at=now)
    )
    await conn.execute(stmt)


async def create_recommendation(
    conn: Any,
    *,
    alert_id: str | None,
    block_id: str | None,
    vineyard_id: str,
    action_text: str,
    priority: int = 2,
    due_by: datetime | None = None,
) -> str:
    """Insert a recommendation linked to an alert.

    Returns the UUID of the newly created recommendation as a string.
    """
    result = await conn.execute(
        recommendations.insert().values(
            alert_id=alert_id,
            block_id=block_id,
            vineyard_id=vineyard_id,
            action_text=action_text,
            priority=priority,
            due_by=due_by,
            is_acknowledged=False,
            acknowledged_at=None,
        ).returning(recommendations.c.id)
    )
    row = result.first()
    return str(row[0])
