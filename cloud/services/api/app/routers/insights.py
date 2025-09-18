from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.nodes import InsightResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=List[InsightResponse])
def list_insights(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    node_id: UUID | None = Query(None),
    type: str | None = Query(None, alias="type"),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
):
    if to_ts is None:
        to_ts = datetime.utcnow()
    if from_ts is None:
        from_ts = to_ts - timedelta(days=7)

    conditions = ["org_id = :org_id", "created_at BETWEEN :from_ts AND :to_ts"]
    params: dict[str, object] = {
        "org_id": str(current_user["org_id"]),
        "from_ts": from_ts,
        "to_ts": to_ts,
        "limit": limit,
    }

    if node_id is not None:
        conditions.append("(node_id IS NULL OR node_id = :node_id)")
        params["node_id"] = str(node_id)

    if type is not None:
        conditions.append("insight_type = :insight_type")
        params["insight_type"] = type

    where_clause = " AND ".join(conditions)
    query = text(
        f"""
        SELECT id, node_id, org_id, insight_type, severity, message, metadata, created_at
        FROM insights
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )

    rows = db.execute(query, params)
    return [InsightResponse(**dict(row)) for row in rows.mappings()]
