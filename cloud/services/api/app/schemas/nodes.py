from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel


class NodeSummary(BaseModel):
    id: UUID
    name: str
    site_id: UUID | None
    org_id: UUID
    hardware_id: str | None
    created_at: datetime
    last_seen: datetime | None = None
    battery_level: float | None = None
    temperature: float | None = None
    moisture: float | None = None


class TelemetryPoint(BaseModel):
    reading_time: datetime
    payload: dict[str, Any]


class InsightResponse(BaseModel):
    id: int
    node_id: UUID | None
    org_id: UUID
    insight_type: str
    severity: str
    message: str
    metadata: dict[str, Any] | None
    created_at: datetime
