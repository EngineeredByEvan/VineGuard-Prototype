from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TelemetrySensors(BaseModel):
    soil_moisture: float | None = Field(None, alias="soilMoisture")
    soil_temp_c: float | None = Field(None, alias="soilTempC")
    air_temp_c: float | None = Field(None, alias="airTempC")
    humidity: float | None = None
    light_lux: float | None = Field(None, alias="lightLux")
    vbat: float | None = None

    @field_validator("soil_moisture")
    @classmethod
    def clamp_soil_moisture(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value > 1.0 and value <= 100:
            # Allow firmware publishing 0-100 instead of 0-1
            return value / 100.0
        return value


class TelemetryPayload(BaseModel):
    ts: datetime
    org_id: str = Field(alias="orgId")
    site_id: str = Field(alias="siteId")
    node_id: str = Field(alias="nodeId")
    fw_version: str = Field(alias="fwVersion")
    sensors: TelemetrySensors
    rssi: int | None = None


class DownlinkParams(BaseModel):
    publish_interval_sec: int | None = Field(None, alias="publishIntervalSec")
    sleep_strategy: Literal["light", "deep", "ultra"] | None = Field(None, alias="sleepStrategy")
    ota_url: str | None = Field(None, alias="otaUrl")


class DownlinkCommand(BaseModel):
    command: Literal["set_config", "ping", "ota_update"]
    params: DownlinkParams | None = None
