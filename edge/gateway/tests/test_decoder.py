"""
test_decoder.py — Unit tests for the VineGuard gateway payload decoder.

Run with: pytest edge/gateway/tests/test_decoder.py -v
"""

from __future__ import annotations

import json
import struct
import time
from pathlib import Path

import pytest

# Make the gateway package importable from this test location
import sys
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from vineguard_gateway.decoder import (
    PayloadDecodeError,
    _crc16_ccitt,
    decode_auto,
    decode_binary,
    decode_compact_json,
    decode_v1_json,
    validate_v1,
)

FIXTURES = Path(__file__).parent / "fixtures"

# ─── CRC helpers ─────────────────────────────────────────────────────────────

def _make_binary_frame(
    soil_pct: float = 28.4,
    at_c: float = 21.3,
    rh_pct: float = 63.2,
    hpa: float = 1007.2,
    lux: int = 24500,
    batt_v: float = 11.5,
    batt_pct: int = 65,
    flags_extra: int = 0,
) -> bytes:
    """Build a minimal VGPP-1 binary frame for test use."""
    PROTOCOL_V1 = 0xA1
    FLAGS_SOIL_VALID  = 1 << 0
    FLAGS_BME280_VALID = 1 << 2
    FLAGS_LUX_VALID   = 1 << 3
    flags = FLAGS_SOIL_VALID | FLAGS_BME280_VALID | FLAGS_LUX_VALID | flags_extra

    buf = bytearray()
    buf.append(PROTOCOL_V1)
    buf += struct.pack("<H", 42)       # seq=42
    buf += struct.pack("<H", flags)
    buf += struct.pack("<H", int(soil_pct * 100))
    buf += struct.pack("<H", 0)        # soil temp encoded (not valid)
    buf += struct.pack("<H", int((at_c + 40) * 10))
    buf += struct.pack("<H", int(rh_pct * 100))
    buf += struct.pack("<H", int(hpa * 10 - 8500))
    lux_b = lux.to_bytes(3, "little")
    buf += lux_b
    buf.append(int(batt_v * 10))
    buf.append(batt_pct)
    crc = _crc16_ccitt(bytes(buf))
    buf += struct.pack("<H", crc)
    return bytes(buf)


# ─── CRC tests ────────────────────────────────────────────────────────────────

class TestCrc:
    def test_known_value(self):
        # CRC-16/CCITT-FALSE of b"123456789" = 0x29B1
        assert _crc16_ccitt(b"123456789") == 0x29B1

    def test_empty(self):
        assert isinstance(_crc16_ccitt(b""), int)


# ─── Binary decode ────────────────────────────────────────────────────────────

class TestDecodeBinary:
    def test_valid_frame_decodes(self):
        frame = _make_binary_frame()
        result = decode_binary(frame, gateway_id="vg-gw-001")
        assert result["schema_version"] == "1.0"
        assert result["meta"]["battery_voltage"] == pytest.approx(11.5, abs=0.1)
        assert result["sensors"]["soil_moisture_pct"] == pytest.approx(28.4, abs=0.01)
        assert result["sensors"]["ambient_temp_c"] == pytest.approx(21.3, abs=0.1)
        assert result["sensors"]["ambient_humidity_pct"] == pytest.approx(63.2, abs=0.1)
        assert result["sensors"]["light_lux"] == 24500.0

    def test_gateway_id_injected(self):
        frame = _make_binary_frame()
        result = decode_binary(frame, gateway_id="gw-test")
        assert result["gateway_id"] == "gw-test"

    def test_crc_mismatch_raises(self):
        frame = bytearray(_make_binary_frame())
        frame[5] ^= 0xFF  # corrupt a byte
        with pytest.raises(PayloadDecodeError, match="CRC"):
            decode_binary(bytes(frame))

    def test_too_short_raises(self):
        with pytest.raises(PayloadDecodeError, match="too short"):
            decode_binary(b"\xA1\x00" * 5)

    def test_wrong_protocol_raises(self):
        frame = bytearray(_make_binary_frame())
        frame[0] = 0xFF
        with pytest.raises(PayloadDecodeError, match="protocol"):
            decode_binary(bytes(frame))

    def test_tier_precision_flag(self):
        FLAGS_TIER_PRECISION = 1 << 6
        frame = _make_binary_frame(flags_extra=FLAGS_TIER_PRECISION)
        result = decode_binary(frame)
        assert result["tier"] == "precision_plus"

    def test_tier_basic_default(self):
        frame = _make_binary_frame()
        result = decode_binary(frame)
        assert result["tier"] == "basic"

    def test_sensor_error_flag(self):
        FLAGS_SENSOR_ERROR = 1 << 8
        frame = _make_binary_frame(flags_extra=FLAGS_SENSOR_ERROR)
        result = decode_binary(frame)
        assert result["meta"]["sensor_ok"] is False

    def test_low_battery_flag(self):
        FLAGS_LOW_BATTERY = 1 << 7
        frame = _make_binary_frame(flags_extra=FLAGS_LOW_BATTERY)
        result = decode_binary(frame)
        assert result["meta"].get("low_battery") is True


# ─── Compact JSON decode ──────────────────────────────────────────────────────

class TestDecodeCompactJson:
    COMPACT = '{"v":1,"id":"vg-node-001","seq":42,"sm":28.4,"at":21.3,"ah":63.2,"p":1007,"l":24500,"bv":11.5,"bp":65,"ok":1,"tier":"basic"}'

    def test_required_fields(self):
        result = decode_compact_json(self.COMPACT, gateway_id="vg-gw-001")
        assert result["schema_version"] == "1.0"
        assert result["device_id"] == "vg-node-001"
        assert result["tier"] == "basic"
        assert result["_sequence"] == 42

    def test_sensor_values(self):
        result = decode_compact_json(self.COMPACT)
        s = result["sensors"]
        assert s["soil_moisture_pct"] == pytest.approx(28.4, abs=0.01)
        assert s["ambient_temp_c"]    == pytest.approx(21.3, abs=0.01)
        assert s["leaf_wetness_pct"]  is None

    def test_meta_values(self):
        result = decode_compact_json(self.COMPACT)
        m = result["meta"]
        assert m["battery_voltage"] == pytest.approx(11.5, abs=0.01)
        assert m["battery_pct"]     == 65
        assert m["sensor_ok"]       is True

    def test_invalid_json_raises(self):
        with pytest.raises(PayloadDecodeError):
            decode_compact_json("not json {{{")

    def test_with_leaf_wetness(self):
        raw = '{"v":1,"id":"vg-003","seq":5,"sm":38.5,"at":19.2,"ah":88,"p":1003,"l":8200,"lw":72.0,"bv":11.9,"bp":78,"ok":1,"tier":"precision_plus"}'
        result = decode_compact_json(raw)
        assert result["sensors"]["leaf_wetness_pct"] == pytest.approx(72.0, abs=0.01)
        assert result["tier"] == "precision_plus"


# ─── V1 JSON pass-through ─────────────────────────────────────────────────────

class TestDecodeV1Json:
    def test_pass_through(self):
        raw = json.dumps({
            "schema_version": "1.0",
            "device_id": "vg-node-001",
            "tier": "basic",
            "sensors": {"soil_moisture_pct": 28.4},
            "meta": {"battery_voltage": 11.5},
        })
        result = decode_v1_json(raw, gateway_id="gw-001")
        assert result["schema_version"] == "1.0"
        assert result["gateway_id"] == "gw-001"

    def test_missing_schema_version_raises(self):
        raw = json.dumps({"device_id": "vg-001", "sensors": {}, "meta": {}})
        with pytest.raises(PayloadDecodeError, match="schema_version"):
            decode_v1_json(raw)

    def test_timestamp_injected_when_absent(self):
        raw = json.dumps({
            "schema_version": "1.0",
            "device_id": "vg-001",
            "sensors": {},
            "meta": {},
        })
        before = int(time.time())
        result = decode_v1_json(raw)
        assert result["timestamp"] >= before


# ─── Auto-detect dispatch ─────────────────────────────────────────────────────

class TestDecodeAuto:
    def test_v1_json_string(self):
        raw = json.dumps({
            "schema_version": "1.0",
            "device_id": "vg-001",
            "sensors": {},
            "meta": {},
        })
        result = decode_auto(raw)
        assert result["schema_version"] == "1.0"

    def test_compact_json_string(self):
        raw = '{"v":1,"id":"vg-002","seq":1,"sm":25.0,"at":20.0,"ah":60.0,"bv":11.5,"bp":60,"ok":1}'
        result = decode_auto(raw)
        assert result["device_id"] == "vg-002"

    def test_vgpayload_prefix_stripped(self):
        raw = 'VGPAYLOAD:{"v":1,"id":"vg-003","seq":2,"sm":30.0,"at":22.0,"ah":65.0,"bv":11.8,"bp":70,"ok":1}'
        result = decode_auto(raw)
        assert result["device_id"] == "vg-003"

    def test_binary_bytes(self):
        frame = _make_binary_frame()
        result = decode_auto(frame)
        assert result["schema_version"] == "1.0"

    def test_legacy_camelcase(self):
        raw = json.dumps({
            "deviceId": "vg-legacy",
            "soilMoisture": 28.0,
            "ambientTempC": 21.0,
            "ambientHumidity": 60.0,
            "lightLux": 20000.0,
            "batteryVoltage": 11.5,
        })
        result = decode_auto(raw)
        assert result["device_id"] == "vg-legacy"
        assert result["sensors"]["soil_moisture_pct"] == 28.0

    def test_completely_invalid_raises(self):
        with pytest.raises(PayloadDecodeError):
            decode_auto("garbage:::not json or binary")


# ─── Validation ───────────────────────────────────────────────────────────────

class TestValidateV1:
    def _base(self) -> dict:
        return {
            "schema_version": "1.0",
            "device_id": "vg-node-001",
            "tier": "basic",
            "sensors": {
                "soil_moisture_pct":    28.4,
                "ambient_temp_c":       21.3,
                "ambient_humidity_pct": 63.2,
                "pressure_hpa":         1007.2,
                "light_lux":            24500.0,
            },
            "meta": {"battery_voltage": 11.5, "battery_pct": 65},
        }

    def test_valid_payload(self):
        ok, reason = validate_v1(self._base())
        assert ok, reason

    def test_missing_device_id(self):
        p = self._base(); del p["device_id"]
        ok, reason = validate_v1(p)
        assert not ok

    def test_device_id_too_short(self):
        p = self._base(); p["device_id"] = "ab"
        ok, reason = validate_v1(p)
        assert not ok

    def test_soil_out_of_range(self):
        p = self._base(); p["sensors"]["soil_moisture_pct"] = 150.0
        ok, reason = validate_v1(p)
        assert not ok

    def test_null_sensors_allowed(self):
        p = self._base()
        p["sensors"]["ambient_temp_c"] = None
        ok, reason = validate_v1(p)
        assert ok, reason

    def test_battery_out_of_range(self):
        p = self._base(); p["meta"]["battery_voltage"] = 30.0
        ok, reason = validate_v1(p)
        assert not ok


# ─── Fixture round-trip tests ─────────────────────────────────────────────────

class TestFixtures:
    @pytest.mark.parametrize("filename", [
        "basic_healthy.json",
        "dry_down_low_moisture.json",
        "precision_plus_mildew_risk.json",
        "missing_bme280.json",
        "low_battery.json",
    ])
    def test_fixture_validates(self, filename):
        payload = json.loads((FIXTURES / filename).read_text())
        ok, reason = validate_v1(payload)
        assert ok, f"{filename}: {reason}"

    def test_compact_json_fixture_roundtrip(self):
        fixture = json.loads((FIXTURES / "compact_json_lora_p2p.json").read_text())
        raw     = fixture["raw"]
        expected = fixture["expected_v1"]
        result = decode_auto(raw, gateway_id="vg-gw-001")
        assert result["device_id"] == expected["device_id"]
        assert result["tier"]      == expected["tier"]
        s = result["sensors"]
        assert s["soil_moisture_pct"] == pytest.approx(expected["sensors"]["soil_moisture_pct"], abs=0.1)
        assert s["ambient_temp_c"]    == pytest.approx(expected["sensors"]["ambient_temp_c"],    abs=0.1)
