from __future__ import annotations

"""Utility script to simulate node telemetry over UDP."""

import argparse
import json
import random
import socket
import time
from datetime import datetime, timezone


def build_payload(org_id: str, site_id: str, node_id: str) -> dict:
    return {
        "orgId": org_id,
        "siteId": site_id,
        "nodeId": node_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "temperature": round(random.uniform(18.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 65.0), 2),
            "battery": round(random.uniform(3.4, 4.1), 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a VineGuard node sending telemetry")
    parser.add_argument("--host", default="127.0.0.1", help="Gateway UDP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=1700, help="Gateway UDP port (default: 1700)")
    parser.add_argument("--org", default="sim-org", help="Organisation identifier")
    parser.add_argument("--site", default="sim-site", help="Site identifier")
    parser.add_argument("--node", default="udp-node-1", help="Node identifier")
    parser.add_argument("--interval", type=float, default=5.0, help="Interval between packets in seconds")
    parser.add_argument("--count", type=int, default=0, help="Number of packets to send (0 for infinite)")

    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.host, args.port)

    sent = 0
    try:
        while True:
            payload = build_payload(args.org, args.site, args.node)
            message = json.dumps(payload).encode("utf-8")
            sock.sendto(message, target)
            sent += 1
            print(f"sent packet {sent} -> {target}: {message.decode('utf-8')}")
            if args.count and sent >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
