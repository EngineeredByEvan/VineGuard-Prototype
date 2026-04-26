#!/usr/bin/env bash
set -euo pipefail
SERIAL="${1:-}"
if [[ -z "$SERIAL" ]]; then
  echo "Usage: $0 <serial> [manifest_path]"
  exit 1
fi
MANIFEST="${2:-firmware/esp32-node/tools/provisioning_manifest.csv}"
python3 firmware/esp32-node/tools/make_keys_header.py --manifest "$MANIFEST" --serial "$SERIAL"
pio run -d firmware/esp32-node -e heltec_wifi_lora_32_V3 --target upload
python3 - "$MANIFEST" "$SERIAL" <<'PY'
import csv,sys
m,s=sys.argv[1],sys.argv[2]
r=next((x for x in csv.DictReader(open(m)) if x['serial']==s),None)
if not r: raise SystemExit('serial missing after generation')
print(f"Label this node: serial={r['serial']} device_id={r['device_id']} dev_eui={r['dev_eui']}")
PY
