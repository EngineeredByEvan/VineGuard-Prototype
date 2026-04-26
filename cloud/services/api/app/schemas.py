from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "viewer"


# ---------------------------------------------------------------------------
# Vineyard
# ---------------------------------------------------------------------------

class VineyardCreate(BaseModel):
    name: str
    region: str
    owner_name: str


class VineyardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str
    owner_name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

class BlockCreate(BaseModel):
    vineyard_id: UUID
    name: str
    variety: str
    area_ha: float | None = None
    row_spacing_m: float | None = None
    reference_lux_peak: float | None = None
    notes: str = ""


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vineyard_id: UUID
    name: str
    variety: str
    area_ha: float | None = None
    row_spacing_m: float | None = None
    reference_lux_peak: float | None = None
    notes: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    block_id: UUID
    device_id: str
    name: str
    tier: str = "basic"
    lat: float | None = None
    lon: float | None = None
    firmware_version: str = "0.0.0"


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    block_id: UUID
    device_id: str
    name: str
    tier: str
    lat: float | None = None
    lon: float | None = None
    installed_at: datetime
    firmware_version: str | None = None
    last_seen_at: datetime | None = None
    battery_voltage: float | None = None
    battery_pct: int | None = None
    rssi_last: int | None = None
    status: str


# ---------------------------------------------------------------------------
# Compound vineyard / block schemas
# ---------------------------------------------------------------------------

class VineyardWithBlocks(VineyardOut):
    blocks: list[BlockOut] = []


class BlockWithNodes(BlockOut):
    nodes: list[NodeOut] = []


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class TelemetryBase(BaseModel):
    device_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{4,64}$")
    soil_moisture: float
    soil_temp_c: float
    ambient_temp_c: float
    ambient_humidity: float
    light_lux: float
    battery_voltage: float


class TelemetryIn(TelemetryBase):
    recorded_at: datetime | None = None
    leaf_wetness_pct: float | None = None
    pressure_hpa: float | None = None


class TelemetryOut(TelemetryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID | None = None
    leaf_wetness_pct: float | None = None
    pressure_hpa: float | None = None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID | None = None
    block_id: UUID | None = None
    vineyard_id: UUID
    rule_key: str
    severity: str
    title: str
    message: str
    is_active: bool
    triggered_at: datetime
    resolved_at: datetime | None = None


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID | None = None
    block_id: UUID | None = None
    vineyard_id: UUID
    action_text: str
    priority: int
    due_by: datetime | None = None
    is_acknowledged: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class BlockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    variety: str
    node_count: int
    active_alert_count: int
    avg_soil_moisture: float | None = None
    avg_temp: float | None = None
    last_reading_at: datetime | None = None


class DashboardOverview(BaseModel):
    vineyard_id: UUID
    vineyard_name: str
    block_summaries: list[BlockSummary]
    total_active_alerts: int
    gdd_season_total: float | None = None
    gdd_date: date | None = None
    online_node_count: int
    stale_node_count: int


# ---------------------------------------------------------------------------
# GDD
# ---------------------------------------------------------------------------

class GDDEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vineyard_id: UUID
    date: date
    gdd_daily: float
    gdd_season_total: float


# ---------------------------------------------------------------------------
# Device provisioning
# ---------------------------------------------------------------------------

class UnregisteredDevice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    last_seen_at: datetime
    reading_count: int


# ---------------------------------------------------------------------------
# Analytics (kept from original)
# ---------------------------------------------------------------------------

class AnalyticsSignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: str
    signal_type: str
    severity: str
    description: str
    created_at: datetime
