from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.publish as publish

from ..config import get_settings


def build_payload(org_id: str, site_id: str, node_id: str) -> dict:
    soil_moisture = max(0.05, min(random.gauss(0.35, 0.05), 0.9))
    payload = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "orgId": org_id,
        "siteId": site_id,
        "nodeId": node_id,
        "fwVersion": "1.0.0",
        "sensors": {
            "soilMoisture": round(soil_moisture, 3),
            "soilTempC": round(random.uniform(12.0, 20.0), 2),
            "airTempC": round(random.uniform(18.0, 32.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "lightLux": int(random.uniform(1000, 50000)),
            "vbat": round(random.uniform(3.5, 4.1), 2),
        },
        "rssi": random.randint(-90, -60),
    }
    return payload


def publish_payload(topic: str, payload: dict) -> None:
    settings = get_settings()
    publish.single(
        topic,
        payload=json.dumps(payload),
        hostname=settings.mqtt_broker_host,
        port=settings.mqtt_broker_port,
        auth={"username": settings.mqtt_username, "password": settings.mqtt_password}
        if settings.mqtt_username
        else None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fake VineGuard telemetry")
    parser.add_argument("org_id", nargs="?", default="demo-org")
    parser.add_argument("site_id", nargs="?", default="niagara-01")
    parser.add_argument("node_id", nargs="?", default="vg-node-0001")
    parser.add_argument("--interval", type=int, default=600, help="Publish interval seconds")
    parser.add_argument("--count", type=int, default=1, help="Number of messages (0 for infinite)")
    args = parser.parse_args()

    topic = f"vineguard/{args.org_id}/{args.site_id}/{args.node_id}/telemetry"

    sent = 0
    while True:
        payload = build_payload(args.org_id, args.site_id, args.node_id)
        publish_payload(topic, payload)
        print(f"Published telemetry -> {topic}")
        sent += 1
        if args.count and sent >= args.count:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
