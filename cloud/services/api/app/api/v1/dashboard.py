from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/overview", response_model=schemas.DashboardOverview)
async def get_dashboard_overview(
    vineyard_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.DashboardOverview:
    """Return an aggregated dashboard overview for a vineyard."""
    # Verify vineyard exists
    vr = await session.execute(
        select(models.vineyards).where(models.vineyards.c.id == vineyard_id)
    )
    vineyard_row = vr.fetchone()
    if vineyard_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vineyard not found")

    vineyard_name = vineyard_row._mapping["name"]

    # Fetch all blocks for the vineyard
    blocks_result = await session.execute(
        select(models.blocks)
        .where(models.blocks.c.vineyard_id == vineyard_id)
        .order_by(models.blocks.c.created_at)
    )
    block_rows = blocks_result.fetchall()

    now = datetime.now(tz=timezone.utc)
    three_hours_ago = now - timedelta(hours=3)
    online_cutoff = now - timedelta(minutes=30)

    block_summaries: list[schemas.BlockSummary] = []
    total_active_alerts = 0
    online_node_count = 0
    stale_node_count = 0

    for block_row in block_rows:
        block_id = block_row._mapping["id"]
        block_name = block_row._mapping["name"]
        block_variety = block_row._mapping["variety"]

        # Node counts and online/stale status
        nodes_result = await session.execute(
            select(models.nodes).where(models.nodes.c.block_id == block_id)
        )
        node_rows = nodes_result.fetchall()
        node_count = len(node_rows)

        for node_row in node_rows:
            last_seen = node_row._mapping["last_seen_at"]
            node_status = node_row._mapping["status"]
            if node_status == "inactive":
                continue
            if last_seen is not None and last_seen >= online_cutoff:
                online_node_count += 1
            else:
                stale_node_count += 1

        # Active alert count for this block
        alerts_result = await session.execute(
            select(func.count()).select_from(models.alerts).where(
                models.alerts.c.block_id == block_id,
                models.alerts.c.is_active == True,  # noqa: E712
            )
        )
        active_alert_count = alerts_result.scalar() or 0
        total_active_alerts += active_alert_count

        # Avg soil moisture, avg ambient_temp, latest reading time for this block (last 3h)
        # We use a subquery to get node IDs in this block
        node_ids = [n._mapping["id"] for n in node_rows]

        avg_soil_moisture: float | None = None
        avg_temp: float | None = None
        last_reading_at: datetime | None = None

        if node_ids:
            telem_result = await session.execute(
                select(
                    func.avg(models.telemetry_readings.c.soil_moisture).label("avg_soil_moisture"),
                    func.avg(models.telemetry_readings.c.ambient_temp_c).label("avg_temp"),
                    func.max(models.telemetry_readings.c.recorded_at).label("last_reading_at"),
                ).where(
                    models.telemetry_readings.c.node_id.in_(node_ids),
                    models.telemetry_readings.c.recorded_at >= three_hours_ago,
                )
            )
            telem_row = telem_result.fetchone()
            if telem_row is not None:
                avg_soil_moisture = telem_row._mapping["avg_soil_moisture"]
                avg_temp = telem_row._mapping["avg_temp"]
                last_reading_at = telem_row._mapping["last_reading_at"]

        block_summaries.append(
            schemas.BlockSummary(
                id=block_id,
                name=block_name,
                variety=block_variety,
                node_count=node_count,
                active_alert_count=active_alert_count,
                avg_soil_moisture=avg_soil_moisture,
                avg_temp=avg_temp,
                last_reading_at=last_reading_at,
            )
        )

    # Latest GDD season total for this vineyard
    gdd_result = await session.execute(
        select(models.gdd_accumulation)
        .where(models.gdd_accumulation.c.vineyard_id == vineyard_id)
        .order_by(models.gdd_accumulation.c.date.desc())
        .limit(1)
    )
    gdd_row = gdd_result.fetchone()
    gdd_season_total: float | None = None
    gdd_date: date | None = None
    if gdd_row is not None:
        gdd_season_total = gdd_row._mapping["gdd_season_total"]
        gdd_date = gdd_row._mapping["date"]

    return schemas.DashboardOverview(
        vineyard_id=vineyard_id,
        vineyard_name=vineyard_name,
        block_summaries=block_summaries,
        total_active_alerts=total_active_alerts,
        gdd_season_total=gdd_season_total,
        gdd_date=gdd_date,
        online_node_count=online_node_count,
        stale_node_count=stale_node_count,
    )


@router.get("/dashboard/gdd", response_model=list[schemas.GDDEntry])
async def get_gdd(
    vineyard_id: UUID = Query(...),
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.GDDEntry]:
    """Return GDD accumulation entries for the last N days for a vineyard."""
    # Verify vineyard exists
    vr = await session.execute(
        select(models.vineyards).where(models.vineyards.c.id == vineyard_id)
    )
    if vr.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vineyard not found")

    since_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date()
    result = await session.execute(
        select(models.gdd_accumulation)
        .where(
            models.gdd_accumulation.c.vineyard_id == vineyard_id,
            models.gdd_accumulation.c.date >= since_date,
        )
        .order_by(models.gdd_accumulation.c.date.asc())
    )
    rows = result.fetchall()
    return [schemas.GDDEntry(**row._mapping) for row in rows]
