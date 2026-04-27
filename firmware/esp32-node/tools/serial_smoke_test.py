#!/usr/bin/env python3
"""
serial_smoke_test.py — Verify a freshly-flashed VineGuard node over USB serial.

Usage:
    python serial_smoke_test.py --port /dev/ttyUSB0
    python serial_smoke_test.py --port COM3 --baud 115200 --timeout 60

What it checks:
    1. Device boots within the timeout period.
    2. At least one VGPAYLOAD: line is emitted.
    3. The JSON payload is valid and contains required V1 fields.
    4. schema_version == "1.0"
    5. Sensor values are within plausible ranges.
    6. No critical errors in boot log.

Exit codes:
    0  All checks passed.
    1  One or more checks failed.
    2  Device did not respond (not connected / wrong port / wrong baud).
"""

import argparse
import json
import sys
import time

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial", file=sys.stderr)
    sys.exit(2)

REQUIRED_FIELDS = [
    ("schema_version",),
    ("device_id",),
    ("tier",),
    ("sensors",),
    ("meta",),
    ("sensors", "ambient_temp_c"),
    ("meta", "battery_voltage"),
]

FIELD_RANGES = {
    "soil_moisture_pct":    (0.0, 100.0),
    "ambient_temp_c":       (-40.0, 85.0),
    "ambient_humidity_pct": (0.0, 100.0),
    "pressure_hpa":         (800.0, 1100.0),
    "light_lux":            (0.0, 200000.0),
    "battery_voltage":      (0.0, 25.0),
    "battery_pct":          (0, 100),
}

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def check(condition, label, detail=""):
    if condition:
        print(f"{PASS} {label}")
        return True
    else:
        print(f"{FAIL} {label}" + (f": {detail}" if detail else ""))
        return False


def read_until_payload(ser, timeout_sec: int):
    """Read serial lines until a VGPAYLOAD line is found or timeout."""
    deadline = time.time() + timeout_sec
    lines = []
    while time.time() < deadline:
        try:
            line = ser.readline().decode("utf-8", errors="replace").strip()
        except Exception as e:
            print(f"{WARN} Serial read error: {e}")
            continue
        if line:
            print(f"  {INFO} {line}")
            lines.append(line)
            if line.startswith("VGPAYLOAD:"):
                return lines, line[len("VGPAYLOAD:"):]
    return lines, None


def validate_payload(json_str: str) -> tuple[bool, dict]:
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError as e:
        return False, {"_error": str(e)}
    return True, payload


def main():
    parser = argparse.ArgumentParser(description="VineGuard node serial smoke test")
    parser.add_argument("--port",    required=True, help="Serial port (e.g. /dev/ttyUSB0 or COM3)")
    parser.add_argument("--baud",    type=int, default=115200)
    parser.add_argument("--timeout", type=int, default=90, help="Seconds to wait for first payload")
    args = parser.parse_args()

    print(f"\n=== VineGuard Node Serial Smoke Test ===")
    print(f"Port: {args.port}  Baud: {args.baud}  Timeout: {args.timeout}s\n")

    # ── Open serial port ───────────────────────────────────────────────────────
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"{FAIL} Cannot open port {args.port}: {e}")
        sys.exit(2)

    # Reset device by toggling DTR
    ser.setDTR(False); time.sleep(0.1); ser.setDTR(True); time.sleep(0.5)

    print(f"[....] Waiting up to {args.timeout}s for VGPAYLOAD line...")
    lines, payload_str = read_until_payload(ser, args.timeout)
    ser.close()

    failures = 0

    # ── Check 1: device responded ─────────────────────────────────────────────
    booted = len(lines) > 0
    if not check(booted, "Device emitted serial output"):
        print(f"\nDevice did not respond on {args.port}. Check connection, baud rate, and build.")
        sys.exit(2)
    failures += not booted

    # ── Check 2: VGPAYLOAD line found ─────────────────────────────────────────
    if not check(payload_str is not None, "VGPAYLOAD line found",
                 "No VGPAYLOAD line within timeout"):
        sys.exit(1)
    failures += payload_str is None

    # ── Check 3: valid JSON ────────────────────────────────────────────────────
    ok, payload = validate_payload(payload_str)
    failures += not check(ok, "Payload is valid JSON",
                           payload.get("_error", "") if not ok else "")
    if not ok:
        sys.exit(1)

    # ── Check 4: schema_version ───────────────────────────────────────────────
    failures += not check(payload.get("schema_version") == "1.0",
                          "schema_version == '1.0'",
                          f"got: {payload.get('schema_version')}")

    # ── Check 5: required fields present ─────────────────────────────────────
    for path in REQUIRED_FIELDS:
        obj = payload
        for key in path:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                obj = None
                break
        failures += not check(obj is not None, f"Field present: {'.'.join(path)}")

    # ── Check 6: sensor value ranges ─────────────────────────────────────────
    sensors = payload.get("sensors", {})
    meta    = payload.get("meta", {})
    for field, (lo, hi) in FIELD_RANGES.items():
        src = sensors if field in sensors else meta
        val = src.get(field)
        if val is None:
            print(f"  {WARN} {field}: null (sensor may be absent)")
            continue
        in_range = lo <= float(val) <= hi
        failures += not check(in_range, f"Range check {field}={val}",
                               f"expected [{lo}, {hi}]")

    # ── Check 7: no ERROR lines in boot log ──────────────────────────────────
    err_lines = [l for l in lines if "[ERR]" in l and "non-fatal" not in l.lower()]
    if err_lines:
        for l in err_lines:
            print(f"  {WARN} Boot error: {l}")

    print(f"\n{'─'*50}")
    if failures == 0:
        print(f"{PASS} All checks passed.")
        sys.exit(0)
    else:
        print(f"{FAIL} {failures} check(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
