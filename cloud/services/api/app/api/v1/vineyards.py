from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user, require_operator

router = APIRouter(tags=["vineyards"])


@router.get("/vineyards", response_model=list[schemas.VineyardOut])
async def list_vineyards(
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.VineyardOut]:
    """Return all vineyards."""
    result = await session.execute(
        select(models.vineyards).order_by(models.vineyards.c.created_at.desc())
    )
    rows = result.fetchall()
    return [schemas.VineyardOut(**row._mapping) for row in rows]


@router.post("/vineyards", response_model=schemas.VineyardOut, status_code=status.HTTP_201_CREATED)
async def create_vineyard(
    payload: schemas.VineyardCreate,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(require_operator),
) -> schemas.VineyardOut:
    """Create a new vineyard (operator+ only)."""
    result = await session.execute(
        models.vineyards.insert()
        .values(
            name=payload.name,
            region=payload.region,
            owner_name=payload.owner_name,
        )
        .returning(*models.vineyards.c)
    )
    await session.commit()
    row = result.fetchone()
    return schemas.VineyardOut(**row._mapping)


@router.get("/vineyards/{vineyard_id}", response_model=schemas.VineyardOut)
async def get_vineyard(
    vineyard_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.VineyardOut:
    """Return a single vineyard by ID."""
    result = await session.execute(
        select(models.vineyards).where(models.vineyards.c.id == vineyard_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vineyard not found")
    return schemas.VineyardOut(**row._mapping)


@router.get("/vineyards/{vineyard_id}/blocks", response_model=list[schemas.BlockOut])
async def list_vineyard_blocks(
    vineyard_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.BlockOut]:
    """Return all blocks belonging to a vineyard."""
    # Verify vineyard exists
    vr = await session.execute(
        select(models.vineyards).where(models.vineyards.c.id == vineyard_id)
    )
    if vr.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vineyard not found")

    result = await session.execute(
        select(models.blocks)
        .where(models.blocks.c.vineyard_id == vineyard_id)
        .order_by(models.blocks.c.created_at.desc())
    )
    rows = result.fetchall()
    return [schemas.BlockOut(**row._mapping) for row in rows]
