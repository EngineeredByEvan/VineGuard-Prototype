#!/usr/bin/env python3
"""
VineGuard Demo Simulator
Reads a scenario JSON file and publishes deterministic MQTT telemetry payloads
for each configured node.

Usage:
    python simulator.py [--host localhost] [--port 1883] [--scenario demo]
                        [--topic vineguard/telemetry]
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# Sensor keys that are clamped to [0, 100]
_PERCENT_CLAMP_KEYS = {"soil_moisture_pct", "ambient_humidity_pct", "leaf_wetness_pct"}

# Sensor keys present only in precision_plus tier
_PRECISION_PLUS_KEYS = {"leaf_wetness_pct"}

# Hard cap for leaf_wetness in mildew scenario
_LEAF_WETNESS_CAP = 95.0


class NodeState:
    """Holds per-node mutable simulation state."""

    def __init__(self, node_cfg: dict) -> None:
        self.device_id: str = node_cfg["device_id"]
        self.gateway_id: str = node_cfg["gateway_id"]
        self.tier: str = node_cfg["tier"]
        self.scenario: str = node_cfg.get("scenario", "healthy")

        # Current sensor values start at base_values
        self.values: dict = dict(node_cfg["base_values"])

        self.drift: dict = node_cfg.get("drift", {})
        self.moisture_floor: float = node_cfg.get("moisture_floor", 0.0)
        self.temp_floor: float = node_cfg.get("temp_floor", -273.15)

        self.battery_voltage: float = node_cfg.get("battery_voltage", 3.80)
        self.battery_pct: int = node_cfg.get("battery_pct", 75)

        self.tick: int = 0

        # Seed per-node RNG from device_id so nodes are independent but
        # deterministic across runs of the same scenario.
        self._rng = random.Random(self.device_id)

    def _noise(self, drift_magnitude: float) -> float:
        """Small noise: ±(10% of |drift| or 0.1 if drift==0)."""
        magnitude = abs(drift_magnitude) * 0.1 if drift_magnitude != 0 else 0.1
        return self._rng.uniform(-magnitude, magnitude)

    def advance(self) -> dict:
        """Advance simulation one tick and return the updated sensor values."""
        self.tick += 1

        for key, base_val in list(self.values.items()):
            drift_val = self.drift.get(key, 0.0)
            noise = self._noise(drift_val)
            new_val = base_val + drift_val + noise

            # Apply floor/ceiling constraints
            if key == "soil_moisture_pct":
                floor = self.moisture_floor if self.moisture_floor is not None else 0.0
                new_val = max(floor, min(100.0, new_val))
            elif key == "ambient_temp_c" and self.temp_floor is not None:
                new_val = max(self.temp_floor, new_val)
            elif key == "leaf_wetness_pct":
                new_val = max(0.0, min(_LEAF_WETNESS_CAP, new_val))
            elif key in _PERCENT_CLAMP_KEYS:
                new_val = max(0.0, min(100.0, new_val))

            self.values[key] = round(new_val, 2)

        return dict(self.values)

    def build_payload(self) -> dict:
        """Build and return the canonical v1 telemetry payload."""
        sensor_values = self.advance()

        sensors = {
            "soil_moisture_pct": sensor_values.get("soil_moisture_pct"),
            "soil_temp_c": sensor_values.get("soil_temp_c"),
            "ambient_temp_c": sensor_values.get("ambient_temp_c"),
            "ambient_humidity_pct": sensor_values.get("ambient_humidity_pct"),
            "pressure_hpa": sensor_values.get("pressure_hpa"),
            "light_lux": sensor_values.get("light_lux"),
            "leaf_wetness_pct": (
                sensor_values.get("leaf_wetness_pct")
                if self.tier == "precision_plus"
                else None
            ),
        }

        return {
            "schema_version": "1.0",
            "device_id": self.device_id,
            "gateway_id": self.gateway_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "tier": self.tier,
            "sensors": sensors,
            "meta": {
                "battery_voltage": self.battery_voltage,
                "battery_pct": self.battery_pct,
                "rssi": self._rng.randint(-90, -60),
                "snr": round(self._rng.uniform(5.0, 12.0), 1),
                "sensor_ok": True,
            },
        }


def load_scenario(scenario_name: str) -> dict:
    """Load a scenario JSON file by name (without .json extension)."""
    path = SCENARIOS_DIR / f"{scenario_name}.json"
    if not path.exists():
        print(f"ERROR: Scenario file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return json.load(f)


def on_connect(client: mqtt.Client, userdata, flags, rc: int) -> None:
    if rc == 0:
        print(f"[mqtt] Connected to broker (rc={rc})")
    else:
        print(f"[mqtt] Connection failed (rc={rc})", file=sys.stderr)
        sys.exit(1)


def on_disconnect(client: mqtt.Client, userdata, rc: int) -> None:
    if rc != 0:
        print(f"[mqtt] Unexpected disconnect (rc={rc})", file=sys.stderr)


def build_client(host: str, port: int) -> mqtt.Client:
    client = mqtt.Client(client_id="vineguard-simulator", clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(host, port, keepalive=60)
    client.loop_start()
    return client


def log_tick(tick: int, node: NodeState) -> None:
    """Print a compact single-line summary for a published reading."""
    v = node.values
    moisture = v.get("soil_moisture_pct", "n/a")
    temp = v.get("ambient_temp_c", "n/a")
    humidity = v.get("ambient_humidity_pct", "n/a")
    lw = v.get("leaf_wetness_pct")

    parts = [
        f"[tick {tick:04d}]",
        f"{node.device_id}:",
        f"moisture={moisture:.1f}%",
        f"temp={temp:.1f}°C",
        f"hum={humidity:.1f}%",
    ]
    if lw is not None:
        parts.append(f"leaf_wet={lw:.1f}%")

    print("  ".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VineGuard demo MQTT telemetry simulator"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("SIMULATOR_MQTT_HOST", "localhost"),
        help="MQTT broker host (default: localhost or SIMULATOR_MQTT_HOST env)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SIMULATOR_MQTT_PORT", "1883")),
        help="MQTT broker port (default: 1883 or SIMULATOR_MQTT_PORT env)",
    )
    parser.add_argument(
        "--scenario",
        default=os.environ.get("SIMULATOR_SCENARIO", "demo"),
        help="Scenario name (default: demo or SIMULATOR_SCENARIO env)",
    )
    parser.add_argument(
        "--topic",
        default="vineguard/telemetry",
        help="MQTT topic to publish on (default: vineguard/telemetry)",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    interval = scenario.get("interval_seconds", 30)

    print(f"VineGuard Simulator — scenario: {scenario['name']}")
    print(f"  Description : {scenario.get('description', '')}")
    print(f"  Nodes       : {len(scenario['nodes'])}")
    print(f"  Interval    : {interval}s")
    print(f"  Broker      : {args.host}:{args.port}")
    print(f"  Topic       : {args.topic}")
    print()

    nodes = [NodeState(n) for n in scenario["nodes"]]

    print(f"[mqtt] Connecting to {args.host}:{args.port} ...")
    client = build_client(args.host, args.port)

    # Give the async connect callback a moment to fire
    time.sleep(1.5)

    tick = 0
    try:
        while True:
            tick += 1
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"\n--- tick {tick:04d}  {ts} ---")

            for node in nodes:
                payload = node.build_payload()
                message = json.dumps(payload)
                result = client.publish(args.topic, message, qos=1)
                result.wait_for_publish()
                log_tick(tick, node)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[simulator] Stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
