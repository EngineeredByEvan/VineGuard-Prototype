from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, ValidationError  # noqa: F401 – re-exported for callers


# ---------------------------------------------------------------------------
# V1 sub-models
# ---------------------------------------------------------------------------

class SensorsV1(BaseModel):
    soil_moisture_pct: float = Field(ge=0, le=100)
    soil_temp_c: float = Field(ge=-40, le=80)
    ambient_temp_c: float = Field(ge=-40, le=60)
    ambient_humidity_pct: float = Field(ge=0, le=100)
    pressure_hpa: float | None = Field(default=None, ge=850, le=1100)
    light_lux: float = Field(ge=0, le=200000)
    leaf_wetness_pct: float | None = Field(default=None, ge=0, le=100)


class MetaV1(BaseModel):
    battery_voltage: float = Field(ge=0, le=5)
    battery_pct: int | None = Field(default=None, ge=0, le=100)
    rssi: int | None = None
    snr: float | None = None
    sensor_ok: bool = True


# ---------------------------------------------------------------------------
# Top-level payload models
# ---------------------------------------------------------------------------

class TelemetryPayloadV1(BaseModel):
    schema_version: str = "1.0"
    device_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{4,64}$")
    gateway_id: str | None = None
    timestamp: int | float | str | None = None
    tier: str = "basic"
    sensors: SensorsV1
    meta: MetaV1


class TelemetryPayloadLegacy(BaseModel):
    deviceId: str = Field(pattern=r"^[a-zA-Z0-9_-]{4,64}$")
    soilMoisture: float = Field(ge=0, le=100)
    soilTempC: float = Field(ge=-40, le=80)
    ambientTempC: float = Field(ge=-40, le=60)
    ambientHumidity: float = Field(ge=0, le=100)
    lightLux: float = Field(ge=0, le=200000)
    batteryVoltage: float = Field(ge=0, le=5)
    timestamp: int | float | str | None = None


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def _parse_timestamp(value: Any) -> datetime | None:
    """Convert a unix epoch (int/float) or ISO-8601 string to an aware datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


# ---------------------------------------------------------------------------
# Public parsing entry point
# ---------------------------------------------------------------------------

def parse_payload(raw: dict) -> dict:
    """Detect format (v1 if has 'schema_version', legacy otherwise).

    Validate with the appropriate Pydantic model and return a normalised dict
    ready for DB insert::

        {
            device_id, soil_moisture, soil_temp_c, ambient_temp_c,
            ambient_humidity, light_lux, battery_voltage, battery_pct,
            leaf_wetness_pct, pressure_hpa, rssi, schema_version, recorded_at
        }

    Raises ``pydantic.ValidationError`` if the payload is invalid.
    """
    if "schema_version" in raw:
        # ---- canonical v1 ----
        validated = TelemetryPayloadV1.model_validate(raw)
        recorded_at = _parse_timestamp(validated.timestamp) or datetime.now(tz=timezone.utc)
        return {
            "device_id": validated.device_id,
            "soil_moisture": validated.sensors.soil_moisture_pct,
            "soil_temp_c": validated.sensors.soil_temp_c,
            "ambient_temp_c": validated.sensors.ambient_temp_c,
            "ambient_humidity": validated.sensors.ambient_humidity_pct,
            "light_lux": validated.sensors.light_lux,
            "battery_voltage": validated.meta.battery_voltage,
            "battery_pct": validated.meta.battery_pct,
            "leaf_wetness_pct": validated.sensors.leaf_wetness_pct,
            "pressure_hpa": validated.sensors.pressure_hpa,
            "rssi": validated.meta.rssi,
            "schema_version": validated.schema_version,
            "recorded_at": recorded_at,
        }
    else:
        # ---- legacy camelCase ----
        validated = TelemetryPayloadLegacy.model_validate(raw)
        recorded_at = _parse_timestamp(validated.timestamp) or datetime.now(tz=timezone.utc)
        return {
            "device_id": validated.deviceId,
            "soil_moisture": validated.soilMoisture,
            "soil_temp_c": validated.soilTempC,
            "ambient_temp_c": validated.ambientTempC,
            "ambient_humidity": validated.ambientHumidity,
            "light_lux": validated.lightLux,
            "battery_voltage": validated.batteryVoltage,
            "battery_pct": None,
            "leaf_wetness_pct": None,
            "pressure_hpa": None,
            "rssi": None,
            "schema_version": "legacy",
            "recorded_at": recorded_at,
        }
