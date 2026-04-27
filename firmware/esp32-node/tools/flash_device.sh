#!/usr/bin/env bash
# flash_device.sh — Provision and flash a VineGuard node (Linux/macOS)
#
# Usage:
#   ./flash_device.sh --serial VG-000001 --env lora_p2p [--manifest /path/manifest.csv] [--port /dev/ttyUSB0]
#
# What it does:
#   1. Validates the serial number against the manifest.
#   2. Generates include/lorawan_keys.h for the node.
#   3. Builds firmware with PlatformIO.
#   4. Uploads to the connected device.
#   5. Prints DevEUI and device_id for labeling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIRMWARE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_DEFAULT="$SCRIPT_DIR/provisioning_manifest.csv"

# ─── Argument parsing ─────────────────────────────────────────────────────────
SERIAL=""
ENV="lora_p2p"
MANIFEST="$MANIFEST_DEFAULT"
PORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --serial)   SERIAL="$2";   shift 2 ;;
        --env)      ENV="$2";      shift 2 ;;
        --manifest) MANIFEST="$2"; shift 2 ;;
        --port)     PORT="$2";     shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [[ -z "$SERIAL" ]]; then
    echo "ERROR: --serial is required" >&2
    exit 1
fi

# ─── Validate tools ───────────────────────────────────────────────────────────
for cmd in python3 pio; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: '$cmd' not found. Install PlatformIO Core and Python 3." >&2
        exit 1
    fi
done

# ─── Check manifest exists ────────────────────────────────────────────────────
if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: Manifest not found: $MANIFEST" >&2
    echo "  Copy provisioning_manifest.example.csv → provisioning_manifest.csv and fill in real values." >&2
    exit 1
fi

# ─── Validate serial in manifest ─────────────────────────────────────────────
if ! grep -q "^$SERIAL," "$MANIFEST"; then
    echo "ERROR: Serial '$SERIAL' not found in $MANIFEST" >&2
    exit 1
fi

echo "=== VineGuard Flash Tool ==="
echo "Serial:   $SERIAL"
echo "Env:      $ENV"
echo "Manifest: $MANIFEST"
echo ""

# ─── Generate keys header ─────────────────────────────────────────────────────
echo "[1/4] Generating lorawan_keys.h..."
python3 "$SCRIPT_DIR/make_keys_header.py" \
    --serial "$SERIAL" \
    --manifest "$MANIFEST"

# ─── Build firmware ───────────────────────────────────────────────────────────
echo "[2/4] Building firmware (env: $ENV)..."
cd "$FIRMWARE_DIR"
pio run --environment "$ENV"

# ─── Flash device ─────────────────────────────────────────────────────────────
echo "[3/4] Flashing device..."
if [[ -n "$PORT" ]]; then
    pio run --environment "$ENV" --target upload --upload-port "$PORT"
else
    pio run --environment "$ENV" --target upload
fi

# ─── Print label info ─────────────────────────────────────────────────────────
echo "[4/4] Flash complete!"
echo ""
DEV_ID=$(grep -m1 "^$SERIAL," "$MANIFEST" | cut -d',' -f2)
DEV_EUI=$(grep -m1 "^$SERIAL," "$MANIFEST" | cut -d',' -f3)
echo "────────────────────────────────────────"
echo "  DEVICE LABEL"
echo "  Serial:   $SERIAL"
echo "  DeviceID: $DEV_ID"
echo "  DevEUI:   $DEV_EUI"
echo "────────────────────────────────────────"
echo "  Print this label and stick it inside the enclosure."
echo ""
