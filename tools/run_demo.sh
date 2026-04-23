#!/usr/bin/env bash
# tools/run_demo.sh — Start the VineGuard V1 demo stack
# Usage: bash tools/run_demo.sh
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${GREEN}[demo]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; }
section() { echo -e "\n${BOLD}==> $*${NC}"; }

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${REPO_ROOT}/cloud/infrastructure"

# ---------------------------------------------------------------------------
# Step 1 — Prerequisite checks
# ---------------------------------------------------------------------------
section "Checking prerequisites"

if ! command -v docker &>/dev/null; then
    error "docker is not installed or not in PATH."
    echo "  Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi
info "docker found: $(docker --version)"

# Support both 'docker compose' (v2 plugin) and 'docker-compose' (v1 standalone)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    error "docker compose (v2 plugin) or docker-compose (v1) not found."
    echo "  Upgrade Docker Desktop or install the compose plugin."
    exit 1
fi
info "compose command: ${COMPOSE}"

if ! command -v python3 &>/dev/null; then
    error "python3 is not in PATH. Install Python 3.10+ to run the seed script."
    exit 1
fi
info "python3 found: $(python3 --version)"

# ---------------------------------------------------------------------------
# Step 2 — Start core services
# ---------------------------------------------------------------------------
section "Starting core services (db, redis, mqtt, api, ingestor, analytics)"

cd "${INFRA_DIR}"

${COMPOSE} up -d db redis mqtt api ingestor analytics
info "Core services started."

# ---------------------------------------------------------------------------
# Step 3 — Wait for API to be healthy
# ---------------------------------------------------------------------------
section "Waiting for API to become healthy"

API_URL="http://localhost:8000/healthz"
MAX_WAIT=90
WAITED=0
INTERVAL=5

info "Polling ${API_URL} (up to ${MAX_WAIT}s) ..."
until curl -sf "${API_URL}" >/dev/null 2>&1; do
    if [[ ${WAITED} -ge ${MAX_WAIT} ]]; then
        error "API did not become healthy within ${MAX_WAIT}s."
        echo ""
        echo "  Troubleshooting:"
        echo "    ${COMPOSE} logs api"
        echo "    ${COMPOSE} logs db"
        exit 1
    fi
    echo -n "."
    sleep ${INTERVAL}
    WAITED=$(( WAITED + INTERVAL ))
done
echo ""
info "API is healthy (responded after ~${WAITED}s)."

# ---------------------------------------------------------------------------
# Step 4 — Seed demo data
# ---------------------------------------------------------------------------
section "Seeding demo data"

cd "${REPO_ROOT}"

# Allow DATABASE_URL override; default matches compose stack
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/vineguard}"

info "Running seed script (DATABASE_URL=${DATABASE_URL}) ..."
python3 "${SCRIPT_DIR}/seed_demo.py"
info "Demo data seeded."

# ---------------------------------------------------------------------------
# Step 5 — Start simulator
# ---------------------------------------------------------------------------
section "Starting demo simulator"

cd "${INFRA_DIR}"

${COMPOSE} --profile demo up -d simulator
info "Simulator started (profile: demo, scenario: demo)."

# ---------------------------------------------------------------------------
# Step 6 — Print instructions
# ---------------------------------------------------------------------------
section "Demo stack is running"

echo ""
echo -e "${BOLD}Services${NC}"
echo "  API          http://localhost:8000"
echo "  API docs     http://localhost:8000/docs"
echo "  Dashboard    http://localhost:5173  (start web dev server below)"
echo ""
echo -e "${BOLD}Demo credentials${NC}"
echo "  Email   : admin@vineguard.demo"
echo "  Password: demo-password-2024"
echo ""
echo -e "${BOLD}Start the web dashboard${NC}"
echo "  cd ${REPO_ROOT}/web"
echo "  npm install"
echo "  npm run dev"
echo ""
echo -e "${BOLD}Follow simulator logs${NC}"
echo "  cd ${INFRA_DIR}"
echo "  ${COMPOSE} logs -f simulator"
echo ""
echo -e "${BOLD}Stop everything${NC}"
echo "  cd ${INFRA_DIR}"
echo "  ${COMPOSE} --profile demo down"
echo ""
echo -e "${BOLD}Demo story${NC}"
echo "  Node vg-node-001  Block A - North Row  Healthy — stable moisture 28-32%"
echo "  Node vg-node-002  Block A - South Row  Dry-down — moisture declining to ~11%"
echo "  Node vg-node-003  Block B - Center     Mildew risk — leaf wetness rising"
echo ""
echo "See docs/DEMO_RUNBOOK.md for the full walkthrough."
echo ""
