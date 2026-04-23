from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user, require_operator

router = APIRouter(tags=["nodes"])


@router.get("/nodes", response_model=list[schemas.NodeOut])
async def list_nodes(
    block_id: UUID | None = Query(default=None),
    node_status: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.NodeOut]:
    """Return all nodes, optionally filtered by block_id and/or status."""
    query = select(models.nodes).order_by(models.nodes.c.installed_at.desc())
    if block_id is not None:
        query = query.where(models.nodes.c.block_id == block_id)
    if node_status is not None:
        query = query.where(models.nodes.c.status == node_status)
    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.NodeOut(**row._mapping) for row in rows]


@router.post("/nodes", response_model=schemas.NodeOut, status_code=status.HTTP_201_CREATED)
async def create_node(
    payload: schemas.NodeCreate,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(require_operator),
) -> schemas.NodeOut:
    """Provision a new node (operator+ only)."""
    # Verify block exists
    br = await session.execute(
        select(models.blocks).where(models.blocks.c.id == payload.block_id)
    )
    if br.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    # Check for duplicate device_id
    existing = await session.execute(
        select(models.nodes).where(models.nodes.c.device_id == payload.device_id)
    )
    if existing.fetchone() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device ID already registered",
        )

    result = await session.execute(
        models.nodes.insert()
        .values(
            block_id=payload.block_id,
            device_id=payload.device_id,
            name=payload.name,
            tier=payload.tier,
            lat=payload.lat,
            lon=payload.lon,
            firmware_version=payload.firmware_version,
            status="active",
        )
        .returning(*models.nodes.c)
    )
    await session.commit()
    row = result.fetchone()
    return schemas.NodeOut(**row._mapping)


@router.get("/nodes/{node_id}", response_model=schemas.NodeOut)
async def get_node(
    node_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.NodeOut:
    """Return a single node by ID."""
    result = await session.execute(
        select(models.nodes).where(models.nodes.c.id == node_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return schemas.NodeOut(**row._mapping)


@router.get("/nodes/{node_id}/telemetry", response_model=list[schemas.TelemetryOut])
async def get_node_telemetry(
    node_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.TelemetryOut]:
    """Return telemetry readings for a single node."""
    # Verify node exists
    nr = await session.execute(
        select(models.nodes).where(models.nodes.c.id == node_id)
    )
    if nr.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    query = (
        select(models.telemetry_readings)
        .where(
            models.telemetry_readings.c.node_id == node_id,
            models.telemetry_readings.c.recorded_at >= since,
        )
        .order_by(models.telemetry_readings.c.recorded_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.TelemetryOut(**row._mapping) for row in rows]
