from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...database import get_session
from ...dependencies import get_current_user, require_operator

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=list[schemas.RecommendationOut])
async def list_recommendations(
    vineyard_id: UUID | None = Query(default=None),
    block_id: UUID | None = Query(default=None),
    is_acknowledged: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(get_current_user),
) -> list[schemas.RecommendationOut]:
    """Return recommendations, filtered by vineyard, block and acknowledgement status."""
    query = (
        select(models.recommendations)
        .where(models.recommendations.c.is_acknowledged == is_acknowledged)
        .order_by(models.recommendations.c.created_at.desc())
        .limit(limit)
    )
    if vineyard_id is not None:
        query = query.where(models.recommendations.c.vineyard_id == vineyard_id)
    if block_id is not None:
        query = query.where(models.recommendations.c.block_id == block_id)

    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.RecommendationOut(**row._mapping) for row in rows]


@router.post(
    "/recommendations/{recommendation_id}/acknowledge",
    response_model=schemas.RecommendationOut,
)
async def acknowledge_recommendation(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_user: schemas.UserOut = Depends(require_operator),
) -> schemas.RecommendationOut:
    """Acknowledge a recommendation (operator+ only)."""
    result = await session.execute(
        select(models.recommendations).where(models.recommendations.c.id == recommendation_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )

    now = datetime.now(tz=timezone.utc)
    update_result = await session.execute(
        models.recommendations.update()
        .where(models.recommendations.c.id == recommendation_id)
        .values(is_acknowledged=True, acknowledged_at=now)
        .returning(*models.recommendations.c)
    )
    await session.commit()
    updated_row = update_result.fetchone()
    return schemas.RecommendationOut(**updated_row._mapping)
