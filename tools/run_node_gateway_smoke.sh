#!/usr/bin/env bash
# VineGuard end-to-end smoke test: gateway (mock mode) → MQTT → cloud ingestor → API
# Requires: docker compose stack running (or SKIP_CLOUD=1 to skip cloud verification)
#
# Usage:
#   ./tools/run_node_gateway_smoke.sh [--skip-cloud] [--payloads N] [--timeout S]
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
#   2 — environment/dependency error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATEWAY_DIR="$REPO_ROOT/edge/gateway"
INFRA_DIR="$REPO_ROOT/cloud/infrastructure"

# ── defaults ─────────────────────────────────────────────────────────────────
SKIP_CLOUD=0
PAYLOAD_COUNT=3
TIMEOUT_SEC=60
GATEWAY_PID=""

# ── colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; FAILURES=$((FAILURES+1)); }
info() { echo -e "${YELLOW}[INFO]${NC} $*"; }
FAILURES=0

# ── argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-cloud)   SKIP_CLOUD=1 ;;
    --payloads)     PAYLOAD_COUNT="$2"; shift ;;
    --timeout)      TIMEOUT_SEC="$2"; shift ;;
    -h|--help)
      sed -n '2,8p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

cleanup() {
  if [[ -n "$GATEWAY_PID" ]] && kill -0 "$GATEWAY_PID" 2>/dev/null; then
    info "Stopping gateway (PID $GATEWAY_PID)..."
    kill "$GATEWAY_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "========================================================"
echo " VineGuard Node–Gateway Smoke Test"
echo " Payloads: $PAYLOAD_COUNT   Timeout: ${TIMEOUT_SEC}s   Skip cloud: $SKIP_CLOUD"
echo "========================================================"

# ── 1. dependency checks ──────────────────────────────────────────────────────
info "Checking dependencies..."

if ! command -v python3 &>/dev/null; then
  echo "python3 not found" >&2; exit 2
fi

if [[ ! -d "$GATEWAY_DIR" ]]; then
  echo "Gateway directory not found: $GATEWAY_DIR" >&2; exit 2
fi

if [[ $SKIP_CLOUD -eq 0 ]]; then
  if ! command -v docker &>/dev/null; then
    info "docker not found — pass --skip-cloud to run gateway-only tests"
    exit 2
  fi
fi

# ── 2. cloud stack ────────────────────────────────────────────────────────────
if [[ $SKIP_CLOUD -eq 0 ]]; then
  info "Checking cloud stack (docker compose)..."
  if ! docker compose -f "$INFRA_DIR/docker-compose.yml" ps --services --filter status=running 2>/dev/null | grep -q "mqtt\|broker"; then
    info "MQTT broker not running — starting cloud stack..."
    docker compose -f "$INFRA_DIR/docker-compose.yml" up -d mqtt broker ingestor 2>&1 | tail -5
    info "Waiting 10 s for services to stabilise..."
    sleep 10
  else
    pass "Cloud stack already running"
  fi

  MQTT_HOST="${MQTT_HOST:-localhost}"
  MQTT_PORT="${MQTT_PORT:-1883}"
  API_BASE="${API_BASE:-http://localhost:8000}"

  # Verify MQTT reachable
  if command -v mosquitto_pub &>/dev/null; then
    if mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -t vineguard/smoke-test -m '{"probe":true}' 2>/dev/null; then
      pass "MQTT broker reachable at $MQTT_HOST:$MQTT_PORT"
    else
      fail "MQTT broker not reachable at $MQTT_HOST:$MQTT_PORT"
    fi
  else
    info "mosquitto_pub not installed — skipping MQTT connectivity check"
  fi

  # Verify API reachable
  if command -v curl &>/dev/null; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/v1/health" 2>/dev/null || echo "000")
    if [[ "$HTTP_STATUS" == "200" ]]; then
      pass "Cloud API healthy ($API_BASE)"
    else
      fail "Cloud API returned HTTP $HTTP_STATUS (expected 200) — $API_BASE/api/v1/health"
    fi
  fi
fi

# ── 3. gateway virtual environment ───────────────────────────────────────────
info "Preparing gateway Python environment..."
VENV_DIR="$GATEWAY_DIR/.venv-smoke"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -e "$GATEWAY_DIR[dev]" 2>&1 | tail -3
pass "Gateway package installed"

# ── 4. configure gateway for smoke test ──────────────────────────────────────
SMOKE_ENV=$(mktemp /tmp/vg-smoke-XXXXXX.env)
cat > "$SMOKE_ENV" <<EOF
ENVIRONMENT=development
LORA_MODE=mock
GATEWAY_ID=vg-smoke-001
MQTT_HOST=${MQTT_HOST:-localhost}
MQTT_PORT=${MQTT_PORT:-1883}
MQTT_TOPIC=vineguard/telemetry
MQTT_USERNAME=
MQTT_PASSWORD=
CA_CERT_PATH=
CLIENT_CERT_PATH=
CLIENT_KEY_PATH=
OFFLINE_CACHE_PATH=/tmp/vg-smoke-cache.jsonl
HEALTH_PORT=18080
EOF

# ── 5. start gateway ──────────────────────────────────────────────────────────
GATEWAY_LOG=$(mktemp /tmp/vg-gateway-XXXXXX.log)
info "Starting gateway in mock mode (log: $GATEWAY_LOG)..."

env $(grep -v '^#' "$SMOKE_ENV" | xargs) \
  "$VENV_DIR/bin/python" -m vineguard_gateway.main \
  > "$GATEWAY_LOG" 2>&1 &
GATEWAY_PID=$!

# Wait for gateway to initialise (up to 10 s)
WAIT=0
until grep -q "Starting gateway" "$GATEWAY_LOG" 2>/dev/null || [[ $WAIT -ge 10 ]]; do
  sleep 1; WAIT=$((WAIT+1))
done

if ! kill -0 "$GATEWAY_PID" 2>/dev/null; then
  fail "Gateway process exited early"
  cat "$GATEWAY_LOG"
  exit 1
fi
pass "Gateway started (PID $GATEWAY_PID)"

# ── 6. wait for published payloads ────────────────────────────────────────────
info "Waiting up to ${TIMEOUT_SEC}s for $PAYLOAD_COUNT published payloads..."
ELAPSED=0
PUBLISHED=0

while [[ $ELAPSED -lt $TIMEOUT_SEC ]]; do
  PUBLISHED=$(grep -c "Published:" "$GATEWAY_LOG" 2>/dev/null || true)
  if [[ $PUBLISHED -ge $PAYLOAD_COUNT ]]; then
    break
  fi
  sleep 2; ELAPSED=$((ELAPSED+2))
done

if [[ $PUBLISHED -ge $PAYLOAD_COUNT ]]; then
  pass "Gateway published $PUBLISHED payload(s) (required $PAYLOAD_COUNT)"
else
  fail "Only $PUBLISHED payload(s) published in ${TIMEOUT_SEC}s (required $PAYLOAD_COUNT)"
  info "Gateway log tail:"
  tail -20 "$GATEWAY_LOG"
fi

# ── 7. validate payload structure ────────────────────────────────────────────
info "Validating payload structure via decoder..."
DECODED_LOG=$(mktemp /tmp/vg-decoded-XXXXXX.log)

# Extract one MQTT payload from the log and run it through the decoder
SAMPLE_PAYLOAD=$(grep -o '"schema_version"[^}]*}' "$GATEWAY_LOG" 2>/dev/null | head -1 || true)
if [[ -z "$SAMPLE_PAYLOAD" ]]; then
  # Extract full JSON from Published log line
  SAMPLE_PAYLOAD=$(grep "Published:" "$GATEWAY_LOG" | head -1 | grep -o '{.*}' || true)
fi

if [[ -n "$SAMPLE_PAYLOAD" ]]; then
  echo "$SAMPLE_PAYLOAD" | "$VENV_DIR/bin/python" \
    "$REPO_ROOT/firmware/esp32-node/tools/decode_payload.py" - \
    > "$DECODED_LOG" 2>&1 && pass "Decoder accepted sample payload" \
    || { fail "Decoder rejected sample payload"; cat "$DECODED_LOG"; }
else
  info "Could not extract payload from log for decoder check (non-critical)"
fi

# ── 8. health endpoint ────────────────────────────────────────────────────────
if command -v curl &>/dev/null; then
  HEALTH=$(curl -s "http://localhost:18080/healthz" 2>/dev/null || echo "")
  if echo "$HEALTH" | grep -q '"status":"ok"'; then
    pass "Gateway health endpoint responded OK"
  else
    fail "Gateway health endpoint did not respond: $HEALTH"
  fi
fi

# ── 9. offline cache smoke test ───────────────────────────────────────────────
info "Testing offline cache (sending to unreachable broker)..."
CACHE_ENV=$(mktemp /tmp/vg-cache-XXXXXX.env)
cat > "$CACHE_ENV" <<EOF
ENVIRONMENT=development
LORA_MODE=mock
GATEWAY_ID=vg-smoke-cache
MQTT_HOST=127.0.0.1
MQTT_PORT=19999
MQTT_TOPIC=vineguard/telemetry
MQTT_USERNAME=
MQTT_PASSWORD=
CA_CERT_PATH=
OFFLINE_CACHE_PATH=/tmp/vg-cache-test.jsonl
HEALTH_PORT=18081
EOF
rm -f /tmp/vg-cache-test.jsonl

CACHE_LOG=$(mktemp /tmp/vg-cache-XXXXXX.log)
env $(grep -v '^#' "$CACHE_ENV" | xargs) \
  "$VENV_DIR/bin/python" -m vineguard_gateway.main \
  > "$CACHE_LOG" 2>&1 &
CACHE_PID=$!
sleep 12
kill "$CACHE_PID" 2>/dev/null || true

if [[ -f /tmp/vg-cache-test.jsonl ]] && [[ $(wc -l < /tmp/vg-cache-test.jsonl) -gt 0 ]]; then
  CACHED_COUNT=$(wc -l < /tmp/vg-cache-test.jsonl)
  pass "Offline cache wrote $CACHED_COUNT line(s) when broker unreachable"
else
  fail "Offline cache file not created when broker unreachable"
fi
rm -f /tmp/vg-cache-test.jsonl "$CACHE_ENV"

# ── 10. cloud data verification (optional) ────────────────────────────────────
if [[ $SKIP_CLOUD -eq 0 ]] && command -v curl &>/dev/null; then
  info "Checking that telemetry reached the cloud API..."
  sleep 5  # Allow ingestor to process

  DEVICE_ID="vg-mock-001"
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "$API_BASE/api/v1/nodes/$DEVICE_ID/telemetry?limit=1" 2>/dev/null || echo "000")
  if [[ "$HTTP_STATUS" == "200" ]]; then
    pass "Cloud API returned telemetry for $DEVICE_ID"
  elif [[ "$HTTP_STATUS" == "404" ]]; then
    info "Node $DEVICE_ID not registered in cloud — register via /api/v1/nodes to complete E2E test"
  else
    fail "Cloud API returned HTTP $HTTP_STATUS for $DEVICE_ID"
  fi
fi

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
if [[ $FAILURES -eq 0 ]]; then
  echo -e "${GREEN}All checks passed${NC}"
  EXIT_CODE=0
else
  echo -e "${RED}$FAILURES check(s) failed${NC}"
  EXIT_CODE=1
fi
echo "========================================================"

rm -f "$SMOKE_ENV" "$GATEWAY_LOG" "$DECODED_LOG" 2>/dev/null || true
exit $EXIT_CODE
