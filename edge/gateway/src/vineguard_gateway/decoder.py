"""
decoder.py — Decode VineGuard node payloads into the V1 MQTT contract.

Supports three input formats:
  1. Full V1 JSON (schema_version present) — pass-through with gateway_id injection.
  2. Compact LoRa P2P JSON (abbreviated keys, produced by LORA_P2P firmware builds).
  3. VGPP-1 binary frames (LORAWAN_OTAA / compact binary, ~22 bytes).

All paths produce a canonical V1 dict matching the ingestor's TelemetryPayloadV1
schema so the cloud stack needs no changes.
"""

from __future__ import annotations

import json
import struct
import time
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

# ─── VGPP-1 binary protocol constants ────────────────────────────────────────
PROTOCOL_V1 = 0xA1

FLAGS_SOIL_VALID         = 1 << 0
FLAGS_SOIL_TEMP_VALID    = 1 << 1
FLAGS_BME280_VALID       = 1 << 2
FLAGS_LUX_VALID          = 1 << 3
FLAGS_LEAF_WETNESS_VALID = 1 << 4
FLAGS_SOLAR_VALID        = 1 << 5
FLAGS_TIER_PRECISION     = 1 << 6
FLAGS_LOW_BATTERY        = 1 << 7
FLAGS_SENSOR_ERROR       = 1 << 8

# ─── Compact JSON key map (firmware → canonical field name) ───────────────────
COMPACT_KEY_MAP = {
    "sm":   "soil_moisture_pct",
    "st":   "soil_temp_c",
    "at":   "ambient_temp_c",
    "ah":   "ambient_humidity_pct",
    "p":    "pressure_hpa",
    "l":    "light_lux",
    "lw":   "leaf_wetness_pct",
    "bv":   "battery_voltage",
    "bp":   "battery_pct",
    "sv":   "solar_voltage",
    "ok":   "sensor_ok",
    "tier": "tier",
}


class PayloadDecodeError(Exception):
    pass


def _crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
        crc &= 0xFFFF
    return crc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decode_binary(data: bytes, gateway_id: Optional[str] = None) -> dict:
    """Decode a VGPP-1 binary frame into a V1 payload dict."""
    if len(data) < 22:
        raise PayloadDecodeError(f"Frame too short: {len(data)} bytes (min 22)")
    if data[0] != PROTOCOL_V1:
        raise PayloadDecodeError(f"Unknown protocol byte 0x{data[0]:02X}")

    stored_crc = struct.unpack_from("<H", data, len(data) - 2)[0]
    calc_crc   = _crc16_ccitt(data[:-2])
    if stored_crc != calc_crc:
        raise PayloadDecodeError(
            f"CRC mismatch: stored=0x{stored_crc:04X} calc=0x{calc_crc:04X}"
        )

    seq   = struct.unpack_from("<H", data, 1)[0]
    flags = struct.unpack_from("<H", data, 3)[0]

    def u16(off): return struct.unpack_from("<H", data, off)[0]
    def u8(off):  return data[off]

    idx = 5
    soil_x100 = u16(idx); idx += 2
    st_enc    = u16(idx); idx += 2
    at_enc    = u16(idx); idx += 2
    rh_x100   = u16(idx); idx += 2
    hpa_enc   = u16(idx); idx += 2
    lux       = u8(idx) | (u8(idx+1) << 8) | (u8(idx+2) << 16); idx += 3
    batt_v_x10 = u8(idx); idx += 1
    batt_pct   = u8(idx); idx += 1

    lw_pct = None
    if flags & FLAGS_LEAF_WETNESS_VALID:
        lw_x100 = u16(idx); idx += 2
        lw_pct  = round(lw_x100 / 100.0, 1)

    solar_v = None
    if flags & FLAGS_SOLAR_VALID:
        solar_v = round(u8(idx) / 10.0, 1); idx += 1

    tier = "precision_plus" if (flags & FLAGS_TIER_PRECISION) else "basic"

    sensors: dict = {}
    sensors["soil_moisture_pct"]   = round(soil_x100 / 100.0, 2) if (flags & FLAGS_SOIL_VALID)    else None
    sensors["soil_temp_c"]         = round(st_enc / 10.0 - 40.0, 1) if (flags & FLAGS_SOIL_TEMP_VALID) else None
    if flags & FLAGS_BME280_VALID:
        sensors["ambient_temp_c"]       = round(at_enc / 10.0 - 40.0, 1)
        sensors["ambient_humidity_pct"] = round(rh_x100 / 100.0, 1)
        sensors["pressure_hpa"]         = round((hpa_enc + 8500) / 10.0, 1)
    else:
        sensors["ambient_temp_c"]       = None
        sensors["ambient_humidity_pct"] = None
        sensors["pressure_hpa"]         = None
    sensors["light_lux"]           = float(lux) if (flags & FLAGS_LUX_VALID)            else None
    sensors["leaf_wetness_pct"]    = lw_pct

    return {
        "schema_version": "1.0",
        "device_id":      "unknown",  # binary frame carries no device_id; must be resolved externally
        "gateway_id":     gateway_id,
        "timestamp":      int(time.time()),
        "tier":           tier,
        "sensors":        sensors,
        "meta": {
            "battery_voltage": round(batt_v_x10 / 10.0, 2),
            "battery_pct":     batt_pct,
            "rssi":            None,
            "snr":             None,
            "sensor_ok":       not bool(flags & FLAGS_SENSOR_ERROR),
            "solar_voltage":   solar_v,
        },
        "_sequence": seq,
    }


def decode_compact_json(raw: str, gateway_id: Optional[str] = None) -> dict:
    """Decode a compact LoRa P2P JSON string into a V1 payload dict."""
    try:
        compact = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PayloadDecodeError(f"JSON parse error: {exc}") from exc

    device_id = compact.get("id", "unknown")
    tier      = compact.get("tier", "basic")
    seq       = compact.get("seq")

    sensors = {
        "soil_moisture_pct":    compact.get("sm"),
        "soil_temp_c":          compact.get("st"),
        "ambient_temp_c":       compact.get("at"),
        "ambient_humidity_pct": compact.get("ah"),
        "pressure_hpa":         compact.get("p"),
        "light_lux":            compact.get("l"),
        "leaf_wetness_pct":     compact.get("lw"),
    }

    return {
        "schema_version": "1.0",
        "device_id":      device_id,
        "gateway_id":     gateway_id,
        "timestamp":      int(time.time()),
        "tier":           tier,
        "sensors":        sensors,
        "meta": {
            "battery_voltage": compact.get("bv"),
            "battery_pct":     compact.get("bp"),
            "rssi":            None,
            "snr":             None,
            "sensor_ok":       bool(compact.get("ok", 1)),
            "solar_voltage":   compact.get("sv"),
        },
        "_sequence": seq,
    }


def decode_v1_json(raw: str, gateway_id: Optional[str] = None) -> dict:
    """Pass through a full V1 JSON payload, injecting gateway_id and timestamp."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PayloadDecodeError(f"JSON parse error: {exc}") from exc

    if "schema_version" not in payload:
        raise PayloadDecodeError("Missing schema_version; use decode_compact_json instead")

    # Inject gateway identity
    payload.setdefault("gateway_id", gateway_id)
    if not payload.get("timestamp"):
        payload["timestamp"] = int(time.time())

    return payload


def decode_auto(raw: bytes | str, gateway_id: Optional[str] = None) -> dict:
    """Auto-detect payload format and decode."""
    if isinstance(raw, bytes):
        # Check for VGPP-1 binary magic byte
        if len(raw) >= 1 and raw[0] == PROTOCOL_V1:
            return decode_binary(raw, gateway_id)
        # Try treating as UTF-8 text
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise PayloadDecodeError("Cannot decode payload as UTF-8 or VGPP-1 binary")

    raw = raw.strip()

    # Strip VGPAYLOAD: prefix emitted by SerialDebugUplink
    if raw.startswith("VGPAYLOAD:"):
        raw = raw[len("VGPAYLOAD:"):]

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PayloadDecodeError(f"Not valid JSON: {exc}") from exc

    # Dispatch on content
    if "schema_version" in obj:
        return decode_v1_json(raw, gateway_id)

    # Compact JSON from LoRa P2P node (has "v", "id", "seq" keys)
    if "v" in obj and "id" in obj:
        return decode_compact_json(raw, gateway_id)

    # Legacy camelCase payload from old firmware (backwards compat)
    if "deviceId" in obj:
        return _decode_legacy(obj, gateway_id)

    raise PayloadDecodeError(f"Unrecognised payload structure: keys={list(obj.keys())[:8]}")


def _decode_legacy(payload: dict, gateway_id: Optional[str]) -> dict:
    """Convert old camelCase payload to V1 format (backwards compatibility)."""
    logger.debug("Converting legacy camelCase payload from device={}", payload.get("deviceId"))
    return {
        "schema_version": "1.0",
        "device_id":      payload.get("deviceId", "unknown"),
        "gateway_id":     gateway_id,
        "timestamp":      payload.get("timestamp") or int(time.time()),
        "tier":           "basic",
        "sensors": {
            "soil_moisture_pct":    payload.get("soilMoisture"),
            "soil_temp_c":          payload.get("soilTempC"),
            "ambient_temp_c":       payload.get("ambientTempC"),
            "ambient_humidity_pct": payload.get("ambientHumidity"),
            "pressure_hpa":         None,
            "light_lux":            payload.get("lightLux"),
            "leaf_wetness_pct":     None,
        },
        "meta": {
            "battery_voltage": payload.get("batteryVoltage"),
            "battery_pct":     None,
            "rssi":            None,
            "snr":             None,
            "sensor_ok":       True,
            "solar_voltage":   None,
        },
    }


def validate_v1(payload: dict) -> tuple[bool, str]:
    """Lightweight validation before MQTT publish. Returns (ok, reason)."""
    required = ["schema_version", "device_id", "sensors", "meta"]
    for field in required:
        if field not in payload:
            return False, f"Missing required field: {field}"

    device_id = payload.get("device_id", "")
    if not (4 <= len(device_id) <= 64):
        return False, f"device_id length invalid: {len(device_id)}"

    sensors = payload.get("sensors", {})
    for field, lo, hi in [
        ("soil_moisture_pct",    0, 100),
        ("ambient_temp_c",       -40, 85),
        ("ambient_humidity_pct", 0, 100),
        ("pressure_hpa",         800, 1100),
        ("light_lux",            0, 200000),
    ]:
        v = sensors.get(field)
        if v is not None and not (lo <= float(v) <= hi):
            return False, f"{field}={v} out of range [{lo}, {hi}]"

    batt = payload.get("meta", {}).get("battery_voltage")
    if batt is not None and not (0 <= float(batt) <= 25):
        return False, f"battery_voltage={batt} out of range"

    return True, "ok"
