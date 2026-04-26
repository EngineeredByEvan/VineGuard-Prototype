#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

REQ = {
    "dev_eui": 16,
    "app_eui": 16,
    "app_key": 32,
}

def validate_hex(value: str, expected_len: int, name: str) -> str:
    value = value.strip()
    if len(value) != expected_len or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"Invalid {name}: expected {expected_len} hex chars")
    return value.upper()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--serial", required=True)
    p.add_argument("--out", default="firmware/esp32-node/include/lorawan_keys.h")
    p.add_argument("--show-secrets", action="store_true")
    args = p.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).read_text(encoding="utf-8").splitlines()))
    row = next((r for r in rows if r["serial"].strip() == args.serial.strip()), None)
    if not row:
        raise SystemExit(f"Serial not found in manifest: {args.serial}")

    dev_eui = validate_hex(row["dev_eui"], REQ["dev_eui"], "dev_eui")
    app_eui = validate_hex(row["app_eui"], REQ["app_eui"], "app_eui")
    app_key = validate_hex(row["app_key"], REQ["app_key"], "app_key")

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                "#pragma once",
                f"static constexpr const char* LORAWAN_DEV_EUI = \"{dev_eui}\";",
                f"static constexpr const char* LORAWAN_APP_EUI = \"{app_eui}\";",
                f"static constexpr const char* LORAWAN_APP_KEY = \"{app_key}\";",
                f"static constexpr const char* PROVISIONED_DEVICE_ID = \"{row['device_id']}\";",
                f"static constexpr const char* PROVISIONED_NODE_SERIAL = \"{row['serial']}\";",
                f"static constexpr const char* PROVISIONED_NODE_TYPE = \"{row['node_type']}\";",
                f"static constexpr const char* PROVISIONED_VINEYARD_ID = \"{row['vineyard_id']}\";",
                f"static constexpr const char* PROVISIONED_BLOCK_ID = \"{row['block_id']}\";",
                "",
            ]
        ),
        encoding="utf-8",
    )

    masked_key = app_key if args.show_secrets else (app_key[:4] + "..." + app_key[-4:])
    print(f"Generated {output} for serial={row['serial']} device_id={row['device_id']} dev_eui={dev_eui} app_key={masked_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
