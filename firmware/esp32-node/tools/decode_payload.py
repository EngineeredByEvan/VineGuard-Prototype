#!/usr/bin/env python3
"""
decode_payload.py — Decode VineGuard node payloads (compact JSON or binary VGPP-1).

Usage:
    # Decode compact JSON from stdin or file
    echo '{"v":1,"id":"vg-001","seq":5,"sm":28.4,"at":21.3,...}' | python decode_payload.py
    python decode_payload.py --file captured.bin --format binary

    # Decode hex-encoded binary frame
    python decode_payload.py --hex "A1010002001C0E..." --format binary

Output:
    V1 JSON payload ready to publish to MQTT (same as simulator format).
"""

import argparse
import json
import struct
import sys
from typing import Optional

# ─── VGPP-1 flags ─────────────────────────────────────────────────────────────
FLAGS_SOIL_VALID          = 1 << 0
FLAGS_SOIL_TEMP_VALID     = 1 << 1
FLAGS_BME280_VALID        = 1 << 2
FLAGS_LUX_VALID           = 1 << 3
FLAGS_LEAF_WETNESS_VALID  = 1 << 4
FLAGS_SOLAR_VALID         = 1 << 5
FLAGS_TIER_PRECISION      = 1 << 6
FLAGS_LOW_BATTERY         = 1 << 7
FLAGS_SENSOR_ERROR        = 1 << 8

PROTOCOL_V1 = 0xA1

# ─── Compact JSON key map ─────────────────────────────────────────────────────
COMPACT_KEY_MAP = {
    "v":    "schema_version",
    "id":   "device_id",
    "seq":  "sequence",
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


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
        crc &= 0xFFFF
    return crc


def decode_binary(data: bytes, device_id: Optional[str] = None) -> dict:
    if len(data) < 22:
        raise ValueError(f"Frame too short: {len(data)} bytes (min 22)")

    if data[0] != PROTOCOL_V1:
        raise ValueError(f"Unknown protocol ID: 0x{data[0]:02X} (expected 0x{PROTOCOL_V1:02X})")

    # Verify CRC
    stored_crc = struct.unpack_from("<H", data, len(data) - 2)[0]
    calc_crc   = crc16_ccitt(data[:-2])
    if stored_crc != calc_crc:
        raise ValueError(f"CRC mismatch: stored=0x{stored_crc:04X} calc=0x{calc_crc:04X}")

    seq   = struct.unpack_from("<H", data, 1)[0]
    flags = struct.unpack_from("<H", data, 3)[0]

    def u16(offset): return struct.unpack_from("<H", data, offset)[0]
    def u8(offset):  return data[offset]

    sensors = {}
    idx = 5

    # soil_moisture
    soil_x100 = u16(idx); idx += 2
    if flags & FLAGS_SOIL_VALID:
        sensors["soil_moisture_pct"] = round(soil_x100 / 100.0, 2)
    else:
        sensors["soil_moisture_pct"] = None

    # soil_temp (always present in frame even if flag=0)
    st_enc = u16(idx); idx += 2
    if flags & FLAGS_SOIL_TEMP_VALID:
        sensors["soil_temp_c"] = round(st_enc / 10.0 - 40.0, 1)
    else:
        sensors["soil_temp_c"] = None

    # BME280
    at_enc = u16(idx); idx += 2
    rh_x100 = u16(idx); idx += 2
    hpa_enc = u16(idx); idx += 2
    if flags & FLAGS_BME280_VALID:
        sensors["ambient_temp_c"]       = round(at_enc / 10.0 - 40.0, 1)
        sensors["ambient_humidity_pct"] = round(rh_x100 / 100.0, 1)
        sensors["pressure_hpa"]         = round((hpa_enc + 8500) / 10.0, 1)
    else:
        sensors["ambient_temp_c"]       = None
        sensors["ambient_humidity_pct"] = None
        sensors["pressure_hpa"]         = None

    # Lux (3 bytes uint24 LE)
    lux = u8(idx) | (u8(idx+1) << 8) | (u8(idx+2) << 16); idx += 3
    sensors["light_lux"] = float(lux) if (flags & FLAGS_LUX_VALID) else None

    # Battery
    batt_v_x10 = u8(idx); idx += 1
    batt_pct   = u8(idx); idx += 1

    # Optional leaf wetness
    if flags & FLAGS_LEAF_WETNESS_VALID:
        lw_x100 = u16(idx); idx += 2
        sensors["leaf_wetness_pct"] = round(lw_x100 / 100.0, 1)
    else:
        sensors["leaf_wetness_pct"] = None

    # Optional solar
    solar_v = None
    if flags & FLAGS_SOLAR_VALID:
        solar_v_x10 = u8(idx); idx += 1
        solar_v = round(solar_v_x10 / 10.0, 1)

    tier = "precision_plus" if (flags & FLAGS_TIER_PRECISION) else "basic"

    return {
        "schema_version": "1.0",
        "device_id":      device_id or "unknown",
        "gateway_id":     None,
        "timestamp":      None,  # gateway assigns wall clock
        "tier":           tier,
        "sensors":        sensors,
        "meta": {
            "battery_voltage": round(batt_v_x10 / 10.0, 2),
            "battery_pct":     batt_pct,
            "solar_voltage":   solar_v,
            "rssi":            None,
            "snr":             None,
            "sensor_ok":       not bool(flags & FLAGS_SENSOR_ERROR),
            "low_battery":     bool(flags & FLAGS_LOW_BATTERY),
        },
        "_decoded_from": "vgpp_binary_v1",
        "_sequence":     seq,
    }


def decode_compact_json(raw: str) -> dict:
    try:
        compact = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse error: {e}")

    sensors = {
        "soil_moisture_pct":   compact.get("sm"),
        "soil_temp_c":         compact.get("st"),
        "ambient_temp_c":      compact.get("at"),
        "ambient_humidity_pct":compact.get("ah"),
        "pressure_hpa":        compact.get("p"),
        "light_lux":           compact.get("l"),
        "leaf_wetness_pct":    compact.get("lw"),
    }

    tier = compact.get("tier", "basic")

    return {
        "schema_version": "1.0",
        "device_id":      compact.get("id", "unknown"),
        "gateway_id":     None,
        "timestamp":      None,
        "tier":           tier,
        "sensors":        sensors,
        "meta": {
            "battery_voltage": compact.get("bv"),
            "battery_pct":     compact.get("bp"),
            "solar_voltage":   compact.get("sv"),
            "rssi":            None,
            "snr":             None,
            "sensor_ok":       bool(compact.get("ok", 1)),
        },
        "_decoded_from": "compact_json",
        "_sequence":     compact.get("seq"),
    }


def main():
    parser = argparse.ArgumentParser(description="Decode VineGuard node payloads")
    parser.add_argument("--format", choices=["auto", "json", "binary"], default="auto")
    parser.add_argument("--hex",    help="Hex-encoded binary frame string")
    parser.add_argument("--file",   help="Binary payload file path")
    parser.add_argument("--device", help="Device ID to inject (binary mode)")
    args = parser.parse_args()

    if args.hex:
        data = bytes.fromhex(args.hex.replace(" ", ""))
        result = decode_binary(data, args.device)
    elif args.file:
        with open(args.file, "rb") as f:
            data = f.read()
        if args.format == "json":
            result = decode_compact_json(data.decode())
        else:
            result = decode_binary(data, args.device)
    else:
        raw = sys.stdin.read().strip()
        if args.format == "binary":
            data = bytes.fromhex(raw.replace(" ", ""))
            result = decode_binary(data, args.device)
        else:
            # Auto-detect: compact JSON if starts with '{'
            if raw.startswith("{"):
                result = decode_compact_json(raw)
            else:
                data = bytes.fromhex(raw.replace(" ", ""))
                result = decode_binary(data, args.device)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
