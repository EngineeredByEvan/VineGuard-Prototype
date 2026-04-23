# VineGuard V1 Demo Runbook

Audience: Solutions engineers, pre-sales, internal demo leads.
Goal: Walk a pilot customer through a live 3-node demo showing healthy monitoring, a low-moisture alert, and a mildew pressure advisory.

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Docker Desktop (or Docker Engine + Compose plugin) | 24+ | Compose v2 required |
| Node.js | 18 LTS | For the web dashboard |
| Python | 3.10+ | For the seed script |
| curl | any | Used by health-check poll |

Ports used: `5432` (Postgres), `6379` (Redis), `1883` (MQTT), `8000` (API), `5173` (web dev server).

---

## Quick Start (one command)

```bash
# From the repo root:
bash tools/run_demo.sh
```

The script:
1. Checks Docker and Python are available
2. Starts `db`, `redis`, `mqtt`, `api`, `ingestor`, `analytics` via docker compose
3. Polls `http://localhost:8000/healthz` until the API is healthy (up to 90 s)
4. Runs `tools/seed_demo.py` to provision demo vineyard/block/node/user data
5. Starts the simulator container (`docker compose --profile demo up -d simulator`)
6. Prints the dashboard URL and credentials

Then start the web dashboard:

```bash
cd web
npm install
npm run dev
# Open http://localhost:5173
```

Demo credentials: `admin@vineguard.demo` / `demo-password-2024`

---

## Manual Step-by-Step

Use this path when you need finer control (e.g., running against a remote DB or a different scenario).

### 1. Start infrastructure

```bash
cd cloud/infrastructure
docker compose up -d db redis mqtt api ingestor analytics
```

Wait for the API:

```bash
until curl -sf http://localhost:8000/healthz; do sleep 5; done && echo "API ready"
```

### 2. Seed demo data

```bash
# From repo root (default DATABASE_URL points to the compose stack)
python3 tools/seed_demo.py

# Custom target:
DATABASE_URL=postgresql://user:pass@host:5432/vineguard python3 tools/seed_demo.py
```

The seed script is idempotent — safe to run multiple times. It inserts:
- Vineyard: Copper Creek Vineyard (Napa Valley, owner: Jordan Hayes)
- Block A: Cabernet Block (Cabernet Sauvignon, 3.2 ha)
- Block B: Pinot Block (Pinot Noir, 1.8 ha)
- Nodes: vg-node-001, vg-node-002 (Block A), vg-node-003 (Block B)
- Gateway: vg-gw-001
- User: admin@vineguard.demo (role: admin)

### 3. Start the simulator

```bash
cd cloud/infrastructure
docker compose --profile demo up -d simulator
```

Watch it publish:

```bash
docker compose logs -f simulator
```

Each tick (every 30 s) produces lines like:

```
--- tick 0001  2026-04-23T10:00:00Z ---
  [tick 0001]  vg-node-001:  moisture=29.6%  temp=21.1°C  hum=62.2%
  [tick 0001]  vg-node-002:  moisture=21.8%  temp=22.6°C  hum=55.0%
  [tick 0001]  vg-node-003:  moisture=31.1%  temp=19.0°C  hum=84.1%  leaf_wet=65.1%
```

### 4. Run a different scenario

```bash
# Frost warning
SIMULATOR_SCENARIO=frost_warning docker compose --profile demo up -d simulator

# All healthy
SIMULATOR_SCENARIO=healthy docker compose --profile demo up -d simulator
```

Available scenarios in `tools/simulator/scenarios/`:
- `demo` — 3-node story: healthy + dry-down + mildew risk (default)
- `frost_warning` — ambient temp declining through 0 °C, high humidity
- `healthy` — all nodes stable, no alerts expected

### 5. Run the simulator locally (no Docker)

```bash
cd tools/simulator
pip install -r requirements.txt
python simulator.py --host localhost --port 1883 --scenario demo
```

---

## Demo Story Narrative

### Opening (30 seconds)

> "This is the Copper Creek Vineyard dashboard. Two growing blocks, three IoT sensor nodes, all streaming live data every 30 seconds. Let me show you the three things a vineyard manager would look at first thing in the morning."

Navigate to the **Overview** page. Point out:
- Vineyard name and region
- GDD (Growing Degree Days) progress bar for the season — this is calculated automatically from temperature readings
- Active alerts badge in the top nav

---

### Scene 1 — Block A, North Row: Healthy Node (1 min)

Navigate to **Blocks > Cabernet Block > Block A - North Row** (vg-node-001).

> "North Row is healthy. Soil moisture is sitting at 29-31% — right in the target window for Cabernet Sauvignon at this growth stage. Temperature and humidity are nominal. No alerts."

Key talking points:
- The sparkline shows moisture stability over the last hour
- Battery at 72% — node has months of life left on a single charge
- Signal quality (RSSI / SNR) shown in the node detail panel

---

### Scene 2 — Block A, South Row: Dry-Down Alert (2 min)

Navigate to **Blocks > Cabernet Block > Block A - South Row** (vg-node-002).

> "South Row is a different story. Moisture has been declining steadily — it's already at 18% and heading toward 11%. The analytics engine has triggered a low_moisture alert."

Show the **Alerts Center** page (filter: Block A, active):
- Alert type: `low_moisture`
- Severity: warning (escalates to critical below 10%)
- Triggered: ~N minutes ago

Navigate to **Recommendations**:
- A recommendation to irrigate Block A - South Row should appear
- The recommendation includes: target moisture, estimated irrigation volume, priority

> "The grower doesn't need to calculate anything. The system tells them what to do and why. They can acknowledge the recommendation right here."

Demonstrate: click **Acknowledge** on the recommendation.

Navigate back to Alerts Center and click **Resolve** on the low_moisture alert.

> "Closing the loop is one click. Everything is timestamped for compliance records."

---

### Scene 3 — Block B, Center: Mildew Pressure Alert (2 min)

Navigate to **Blocks > Pinot Block > Block B - Center** (vg-node-003).

> "Block B has our Precision+ node — it adds a leaf wetness sensor. Right now leaf wetness is at 65% and humidity is 84%. The temperature is in the 19-22 °C range — that's the classic window for powdery mildew infection."

Show the **Alerts Center** page (filter: Block B):
- Alert type: `mildew_risk` (MPI — Mildew Pressure Index)
- The analytics engine runs the Gubler-Thomas model in the background

> "Powdery mildew can devastate a Pinot Noir block in 48 hours. Catching it here, before visible symptoms appear, is worth thousands of dollars per hectare."

Navigate to **Recommendations**:
- Spray advisory with suggested product window, based on infection period hours

> "The Precision+ tier unlocks this class of agronomic intelligence. Basic nodes catch water stress; Precision+ catches disease pressure."

---

### Scene 4 — Wrap / Questions (1 min)

Navigate back to **Overview**:

> "Three nodes, two blocks, three distinct scenarios — all running live. In a real deployment you'd have tens or hundreds of nodes per vineyard, and the same analytics engine scales with them. Every alert, every recommendation, every reading is stored in TimescaleDB — so you can query historical trends, export for your agronomist, or feed your own BI tools via the REST API."

Show `http://localhost:8000/docs` briefly to demonstrate the OpenAPI spec.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/vineguard` | Seed script DB target |
| `SIMULATOR_MQTT_HOST` | `mqtt` (container) / `localhost` (local) | MQTT broker host |
| `SIMULATOR_MQTT_PORT` | `1883` | MQTT broker port |
| `SIMULATOR_SCENARIO` | `demo` | Scenario file name (without .json) |
| `SIMULATOR_TOPIC` | `vineguard/telemetry` | MQTT publish topic |

---

## Troubleshooting

### MQTT not connecting

```bash
# Check broker is up
docker compose logs mqtt

# Test plain connection manually
docker compose exec mqtt mosquitto_pub -h localhost -p 1883 -t test -m hello
```

If the broker shows TLS errors: the compose stack uses plain port 1883 for local dev. Ensure `mosquitto.conf` has `listener 1883` without `tls_version`.

### Database not seeded / tables missing

```bash
# Check DB init logs
docker compose logs db | grep -i error

# Connect directly
psql postgresql://postgres:postgres@localhost:5432/vineguard -c '\dt'
```

If the `vineyards` table is missing, the init SQL did not run. Remove the volume and restart:

```bash
docker compose down -v
docker compose up -d db
# wait ~15s for init to complete
python3 tools/seed_demo.py
```

### Port conflict on 5432 / 1883 / 8000

Stop the conflicting process or change the host port in `docker-compose.yml`:

```yaml
ports:
  - "15432:5432"   # use a different host port
```

Then update `DATABASE_URL` accordingly.

### API returns 500 on /healthz

```bash
docker compose logs api | tail -30
```

Common cause: DB not ready when API starts. Restart the API:

```bash
docker compose restart api
```

### Simulator exits immediately

```bash
docker compose logs simulator
```

Common cause: MQTT broker not healthy yet. The simulator retries the connection once. If the broker takes >5 s to become healthy, restart the simulator after the broker is up:

```bash
docker compose --profile demo restart simulator
```

### No alerts appearing after ~5 minutes

The analytics scheduler runs every 60 s by default. Check:

```bash
docker compose logs analytics | tail -20
```

Ensure the ingestor is writing readings:

```bash
docker compose logs ingestor | grep "inserted\|error" | tail -20
```

---

## Stopping the Demo

```bash
cd cloud/infrastructure

# Stop everything and remove containers (keep data volume)
docker compose --profile demo down

# Stop and also wipe the DB volume (clean slate for next run)
docker compose --profile demo down -v
```

To stop only the simulator:

```bash
docker compose --profile demo stop simulator
```
