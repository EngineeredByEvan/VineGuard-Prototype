#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

import serial

p = argparse.ArgumentParser()
p.add_argument("--port", required=True)
p.add_argument("--baud", type=int, default=115200)
p.add_argument("--timeout", type=int, default=45)
a = p.parse_args()

with serial.Serial(a.port, a.baud, timeout=1) as ser:
    start = time.time()
    while time.time() - start < a.timeout:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        if line.startswith("{"):
            payload = json.loads(line)
            required = ["schema_version", "device_id", "sensors", "meta"]
            missing = [k for k in required if k not in payload]
            if missing:
                raise SystemExit(f"invalid payload, missing={missing}")
            print("PASS: telemetry payload detected")
            raise SystemExit(0)
raise SystemExit("No telemetry payload detected within timeout")
