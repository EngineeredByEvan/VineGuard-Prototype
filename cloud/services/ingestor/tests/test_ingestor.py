"""Tests for ingestor payload parsing and validation."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ingestor.schemas import (
    TelemetryPayloadLegacy,
    TelemetryPayloadV1,
    parse_payload,
)

# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

VALID_V1 = {
    "schema_version": "1.0",
    "device_id": "vg-node-001",
    "gateway_id": "vg-gw-001",
    "timestamp": 1700000000,
    "tier": "basic",
    "sensors": {
        "soil_moisture_pct": 23.5,
        "soil_temp_c": 18.2,
        "ambient_temp_c": 21.3,
        "ambient_humidity_pct": 65.4,
        "pressure_hpa": 1013.2,
        "light_lux": 245.0,
        "leaf_wetness_pct": None,
    },
    "meta": {
        "battery_voltage": 3.87,
        "battery_pct": 72,
        "rssi": -85,
        "snr": 7.5,
        "sensor_ok": True,
    },
}

VALID_LEGACY = {
    "deviceId": "vineguard-node-001",
    "soilMoisture": 57.2,
    "soilTempC": 18.5,
    "ambientTempC": 21.3,
    "ambientHumidity": 63.2,
    "lightLux": 245.0,
    "batteryVoltage": 3.97,
    "timestamp": 1700000000,
}

# ---------------------------------------------------------------------------
# V1 parsing
# ---------------------------------------------------------------------------

class TestV1Parsing:
    def test_v1_payload_parses_correctly(self):
        result = parse_payload(VALID_V1)
        assert result["device_id"] == "vg-node-001"
        assert result["soil_moisture"] == pytest.approx(23.5)
        assert result["soil_temp_c"] == pytest.approx(18.2)
        assert result["ambient_temp_c"] == pytest.approx(21.3)
        assert result["ambient_humidity"] == pytest.approx(65.4)
        assert result["light_lux"] == pytest.approx(245.0)
        assert result["battery_voltage"] == pytest.approx(3.87)
        assert result["battery_pct"] == 72
        assert result["rssi"] == -85
        assert result["pressure_hpa"] == pytest.approx(1013.2)
        assert result["leaf_wetness_pct"] is None
        assert result["schema_version"] == "1.0"

    def test_v1_normalised_keys_present(self):
        result = parse_payload(VALID_V1)
        expected_keys = {
            "device_id", "soil_moisture", "soil_temp_c", "ambient_temp_c",
            "ambient_humidity", "light_lux", "battery_voltage", "battery_pct",
            "leaf_wetness_pct", "pressure_hpa", "rssi", "schema_version", "recorded_at",
        }
        assert expected_keys == set(result.keys())

    def test_v1_model_validates(self):
        model = TelemetryPayloadV1.model_validate(VALID_V1)
        assert model.device_id == "vg-node-001"
        assert model.sensors.soil_moisture_pct == pytest.approx(23.5)
        assert model.meta.battery_pct == 72

    def test_v1_timestamp_unix_int(self):
        result = parse_payload(VALID_V1)
        expected = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        assert result["recorded_at"] == expected

    def test_v1_timestamp_iso_string(self):
        payload = {**VALID_V1, "timestamp": "2023-11-14T22:13:20+00:00"}
        result = parse_payload(payload)
        assert isinstance(result["recorded_at"], datetime)
        assert result["recorded_at"].tzinfo is not None

    def test_v1_timestamp_iso_z_suffix(self):
        payload = {**VALID_V1, "timestamp": "2023-11-14T22:13:20Z"}
        result = parse_payload(payload)
        assert result["recorded_at"].tzinfo is not None

    def test_v1_null_timestamp_defaults_to_now(self):
        payload = {**VALID_V1, "timestamp": None}
        before = datetime.now(tz=timezone.utc)
        result = parse_payload(payload)
        after = datetime.now(tz=timezone.utc)
        assert before <= result["recorded_at"] <= after


# ---------------------------------------------------------------------------
# Legacy parsing
# ---------------------------------------------------------------------------

class TestLegacyParsing:
    def test_legacy_payload_parses_correctly(self):
        result = parse_payload(VALID_LEGACY)
        assert result["device_id"] == "vineguard-node-001"
        assert result["soil_moisture"] == pytest.approx(57.2)
        assert result["soil_temp_c"] == pytest.approx(18.5)
        assert result["ambient_temp_c"] == pytest.approx(21.3)
        assert result["ambient_humidity"] == pytest.approx(63.2)
        assert result["light_lux"] == pytest.approx(245.0)
        assert result["battery_voltage"] == pytest.approx(3.97)
        assert result["schema_version"] == "legacy"

    def test_legacy_normalised_keys_present(self):
        result = parse_payload(VALID_LEGACY)
        expected_keys = {
            "device_id", "soil_moisture", "soil_temp_c", "ambient_temp_c",
            "ambient_humidity", "light_lux", "battery_voltage", "battery_pct",
            "leaf_wetness_pct", "pressure_hpa", "rssi", "schema_version", "recorded_at",
        }
        assert expected_keys == set(result.keys())

    def test_legacy_optional_fields_are_none(self):
        result = parse_payload(VALID_LEGACY)
        assert result["battery_pct"] is None
        assert result["leaf_wetness_pct"] is None
        assert result["pressure_hpa"] is None
        assert result["rssi"] is None

    def test_legacy_model_validates(self):
        model = TelemetryPayloadLegacy.model_validate(VALID_LEGACY)
        assert model.deviceId == "vineguard-node-001"
        assert model.soilMoisture == pytest.approx(57.2)

    def test_legacy_timestamp_unix_int(self):
        result = parse_payload(VALID_LEGACY)
        expected = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        assert result["recorded_at"] == expected

    def test_legacy_timestamp_iso_string(self):
        payload = {**VALID_LEGACY, "timestamp": "2023-11-14T22:13:20Z"}
        result = parse_payload(payload)
        assert isinstance(result["recorded_at"], datetime)
        assert result["recorded_at"].tzinfo is not None

    def test_legacy_null_timestamp_defaults_to_now(self):
        payload = {**VALID_LEGACY, "timestamp": None}
        before = datetime.now(tz=timezone.utc)
        result = parse_payload(payload)
        after = datetime.now(tz=timezone.utc)
        assert before <= result["recorded_at"] <= after


# ---------------------------------------------------------------------------
# Validation errors – V1
# ---------------------------------------------------------------------------

class TestV1ValidationErrors:
    def test_invalid_soil_moisture_above_max(self):
        payload = dict(VALID_V1)
        payload["sensors"] = {**VALID_V1["sensors"], "soil_moisture_pct": 101.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_soil_moisture_below_min(self):
        payload = dict(VALID_V1)
        payload["sensors"] = {**VALID_V1["sensors"], "soil_moisture_pct": -1.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_soil_temp_above_max(self):
        payload = dict(VALID_V1)
        payload["sensors"] = {**VALID_V1["sensors"], "soil_temp_c": 81.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_ambient_temp_above_max(self):
        payload = dict(VALID_V1)
        payload["sensors"] = {**VALID_V1["sensors"], "ambient_temp_c": 61.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_battery_voltage_above_max(self):
        payload = dict(VALID_V1)
        payload["meta"] = {**VALID_V1["meta"], "battery_voltage": 6.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_pressure_below_min(self):
        payload = dict(VALID_V1)
        payload["sensors"] = {**VALID_V1["sensors"], "pressure_hpa": 800.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_missing_sensors_field(self):
        payload = {k: v for k, v in VALID_V1.items() if k != "sensors"}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_missing_meta_field(self):
        payload = {k: v for k, v in VALID_V1.items() if k != "meta"}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_device_id_too_short(self):
        payload = dict(VALID_V1)
        payload["device_id"] = "ab"  # less than 4 chars
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_device_id_invalid_chars(self):
        payload = dict(VALID_V1)
        payload["device_id"] = "vg node@001"  # spaces and @ not allowed
        with pytest.raises(ValidationError):
            parse_payload(payload)


# ---------------------------------------------------------------------------
# Validation errors – Legacy
# ---------------------------------------------------------------------------

class TestLegacyValidationErrors:
    def test_invalid_soil_moisture_above_max(self):
        payload = {**VALID_LEGACY, "soilMoisture": 200.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_invalid_soil_moisture_below_min(self):
        payload = {**VALID_LEGACY, "soilMoisture": -5.0}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_missing_required_field_soil_moisture(self):
        payload = {k: v for k, v in VALID_LEGACY.items() if k != "soilMoisture"}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_missing_required_field_device_id(self):
        payload = {k: v for k, v in VALID_LEGACY.items() if k != "deviceId"}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_missing_required_field_battery_voltage(self):
        payload = {k: v for k, v in VALID_LEGACY.items() if k != "batteryVoltage"}
        with pytest.raises(ValidationError):
            parse_payload(payload)

    def test_device_id_pattern_spaces(self):
        payload = {**VALID_LEGACY, "deviceId": "bad id!"}
        with pytest.raises(ValidationError):
            parse_payload(payload)
