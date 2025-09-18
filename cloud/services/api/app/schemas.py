from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class TelemetryOut(TelemetryBase):
    id: UUID
    recorded_at: datetime


class AnalyticsSignal(BaseModel):
    id: UUID
    device_id: str
    signal_type: str
    severity: str
    description: str
    created_at: datetime
