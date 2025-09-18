from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.nodes import NodeSummary, TelemetryPoint

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=List[NodeSummary])
def list_nodes(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = text(
        """
        SELECT n.id, n.name, n.site_id, n.org_id, n.hardware_id, n.created_at,
               ns.last_seen, ns.battery_level, ns.temperature, ns.moisture
        FROM nodes n
        LEFT JOIN node_status ns ON ns.node_id = n.id
        WHERE n.org_id = :org_id
        ORDER BY n.created_at DESC
        """
    )
    rows = db.execute(query, {"org_id": str(current_user["org_id"])})
    return [NodeSummary(**dict(row)) for row in rows.mappings()]


@router.get("/{node_id}/telemetry", response_model=List[TelemetryPoint])
def node_telemetry(
    node_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    limit: int = Query(200, ge=1, le=1000),
):
    if from_ts is None:
        from_ts = datetime.utcnow() - timedelta(hours=24)
    if to_ts is None:
        to_ts = datetime.utcnow()

    org_id = current_user["org_id"]

    node = db.execute(
        text("SELECT id FROM nodes WHERE id = :id AND org_id = :org_id"),
        {"id": str(node_id), "org_id": str(org_id)},
    ).first()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    query = text(
        """
        SELECT reading_time, payload
        FROM telemetry_raw
        WHERE node_id = :node_id AND org_id = :org_id
          AND reading_time BETWEEN :from_ts AND :to_ts
        ORDER BY reading_time DESC
        LIMIT :limit
        """
    )

    rows = db.execute(
        query,
        {
            "node_id": str(node_id),
            "org_id": str(org_id),
            "from_ts": from_ts,
            "to_ts": to_ts,
            "limit": limit,
        },
    )

    return [TelemetryPoint(**dict(row)) for row in rows.mappings()]
