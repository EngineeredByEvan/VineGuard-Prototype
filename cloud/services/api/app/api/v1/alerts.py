from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user, require_operator

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[schemas.AlertOut])
async def list_alerts(
    vineyard_id: UUID | None = Query(default=None),
    block_id: UUID | None = Query(default=None),
    is_active: bool = Query(default=True),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.AlertOut]:
    """Return alerts, filtered by vineyard, block, active status and severity."""
    query = (
        select(models.alerts)
        .where(models.alerts.c.is_active == is_active)
        .order_by(models.alerts.c.triggered_at.desc())
        .limit(limit)
    )
    if vineyard_id is not None:
        query = query.where(models.alerts.c.vineyard_id == vineyard_id)
    if block_id is not None:
        query = query.where(models.alerts.c.block_id == block_id)
    if severity is not None:
        query = query.where(models.alerts.c.severity == severity)

    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.AlertOut(**row._mapping) for row in rows]


@router.post("/alerts/{alert_id}/resolve", response_model=schemas.AlertOut)
async def resolve_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(require_operator),
) -> schemas.AlertOut:
    """Resolve an active alert (operator+ only)."""
    result = await session.execute(
        select(models.alerts).where(models.alerts.c.id == alert_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    now = datetime.now(tz=timezone.utc)
    update_result = await session.execute(
        models.alerts.update()
        .where(models.alerts.c.id == alert_id)
        .values(is_active=False, resolved_at=now)
        .returning(*models.alerts.c)
    )
    await session.commit()
    updated_row = update_result.fetchone()
    return schemas.AlertOut(**updated_row._mapping)
