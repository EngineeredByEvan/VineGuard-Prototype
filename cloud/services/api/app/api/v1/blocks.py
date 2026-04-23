from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user, require_operator

router = APIRouter(tags=["blocks"])


@router.get("/blocks", response_model=list[schemas.BlockOut])
async def list_blocks(
    vineyard_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.BlockOut]:
    """Return all blocks, optionally filtered by vineyard_id."""
    query = select(models.blocks).order_by(models.blocks.c.created_at.desc())
    if vineyard_id is not None:
        query = query.where(models.blocks.c.vineyard_id == vineyard_id)
    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.BlockOut(**row._mapping) for row in rows]


@router.post("/blocks", response_model=schemas.BlockOut, status_code=status.HTTP_201_CREATED)
async def create_block(
    payload: schemas.BlockCreate,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(require_operator),
) -> schemas.BlockOut:
    """Create a new block (operator+ only)."""
    # Verify vineyard exists
    vr = await session.execute(
        select(models.vineyards).where(models.vineyards.c.id == payload.vineyard_id)
    )
    if vr.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vineyard not found")

    result = await session.execute(
        models.blocks.insert()
        .values(
            vineyard_id=payload.vineyard_id,
            name=payload.name,
            variety=payload.variety,
            area_ha=payload.area_ha,
            row_spacing_m=payload.row_spacing_m,
            reference_lux_peak=payload.reference_lux_peak,
            notes=payload.notes,
        )
        .returning(*models.blocks.c)
    )
    await session.commit()
    row = result.fetchone()
    return schemas.BlockOut(**row._mapping)


@router.get("/blocks/{block_id}", response_model=schemas.BlockWithNodes)
async def get_block(
    block_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.BlockWithNodes:
    """Return a single block with its nodes."""
    result = await session.execute(
        select(models.blocks).where(models.blocks.c.id == block_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    block_data = dict(row._mapping)

    nodes_result = await session.execute(
        select(models.nodes)
        .where(models.nodes.c.block_id == block_id)
        .order_by(models.nodes.c.installed_at.desc())
    )
    node_rows = nodes_result.fetchall()
    block_data["nodes"] = [schemas.NodeOut(**n._mapping) for n in node_rows]

    return schemas.BlockWithNodes(**block_data)


@router.get("/blocks/{block_id}/telemetry", response_model=list[schemas.TelemetryOut])
async def get_block_telemetry(
    block_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.TelemetryOut]:
    """Return telemetry for all nodes belonging to a block."""
    # Verify block exists
    br = await session.execute(
        select(models.blocks).where(models.blocks.c.id == block_id)
    )
    if br.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    query = (
        select(models.telemetry_readings)
        .where(
            models.telemetry_readings.c.node_id.in_(
                select(models.nodes.c.id).where(models.nodes.c.block_id == block_id)
            ),
            models.telemetry_readings.c.recorded_at >= since,
        )
        .order_by(models.telemetry_readings.c.recorded_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.TelemetryOut(**row._mapping) for row in rows]
