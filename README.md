# VineGuard™

VineGuard is a vineyard intelligence platform — not just telemetry. It combines IoT sensor nodes, a LoRa gateway bridge, a cloud analytics engine, and a decision-ready web dashboard to give growers actionable insight: irrigation recommendations, disease pressure alerts, and growing degree day tracking, all from a single interface.

```
/vineguard
  /firmware/esp32-node          # ESP32 (Arduino/FreeRTOS) sensor firmware
  /edge/gateway                 # Python LoRa <-> MQTT bridge
  /cloud                        # FastAPI + TimescaleDB analytics stack
  /web                          # React + TypeScript dashboard
  /tools                        # Demo simulator and seed scripts
  /docs                         # Runbooks, ADRs, API samples
```

## Quick Start — Demo

The fastest path to a running demo is a single script:

```bash
bash tools/run_demo.sh
```

This starts the full cloud stack via Docker Compose, seeds the 3-node demo vineyard, and launches the telemetry simulator. Then open the web dashboard:

```bash
cd web
npm install
npm run dev
# Dashboard: http://localhost:5173
```

Demo credentials: `admin@vineguard.demo` / `demo-password-2024`

See [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md) for the full walkthrough and demo story.

---

## The 3-Node Demo Story

| Node | Block | Scenario | What to show |
|------|-------|----------|--------------|
| vg-node-001 (basic) | Cabernet Block - North Row | Healthy | Stable moisture 28-32%, good signal, no alerts |
| vg-node-002 (basic) | Cabernet Block - South Row | Dry-Down | Moisture declining 22% → 11%, triggers `low_moisture` alert + irrigation recommendation |
| vg-node-003 (precision_plus) | Pinot Block - Center | Mildew Risk | Leaf wetness rising, humidity 84%, triggers `mildew_risk` alert + spray advisory |

Vineyard: **Copper Creek Vineyard**, Napa Valley — owner: Jordan Hayes

---

## Dashboard Views

1. **Overview** — vineyard-level summary: active alert count, GDD progress, node status map
2. **Blocks** — list of growing blocks with aggregate health indicators
3. **Block Detail** — per-block sensor timeline, node list, and recent alerts
4. **Alerts Center** — filterable alert feed; resolve alerts in one click
5. **Recommendations** — AI-generated action items (irrigate, spray, inspect); acknowledge and close the loop

---

## Architecture Overview

```
[ESP32 nodes] --LoRa--> [Gateway bridge] --MQTT--> [Mosquitto]
                                                        |
                                               [Ingestor worker]
                                                        |
                                               [TimescaleDB]
                                                        |
                                          [Analytics scheduler] --> alerts / recommendations
                                                        |
                                               [FastAPI REST]
                                                        |
                                               [React dashboard]
```

- **MQTT broker**: Mosquitto — plain port 1883 (local dev), TLS port 8883 (production)
- **Database**: TimescaleDB (Postgres extension) — hypertable on `telemetry_readings`
- **Cache / streaming**: Redis pub/sub
- **Analytics**: rule-based engine (moisture, mildew MPI, frost, GDD, canopy lux)

---

## Manual Stack Setup

### Cloud stack

```bash
cd cloud/infrastructure
docker compose up -d --build
```

Services started: `db` (TimescaleDB), `redis`, `mqtt`, `api` (port 8000), `ingestor`, `analytics`.

### Seed demo data

```bash
python3 tools/seed_demo.py
```

### Simulator (standalone)

```bash
cd tools/simulator
pip install -r requirements.txt
python simulator.py --scenario demo
# Other scenarios: frost_warning, healthy
```

### Web dashboard

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

### Edge gateway

```bash
cd edge/gateway
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
vineguard-gateway
```

---

## Security Notes

- MQTT is TLS-enabled on port 8883 for production gateway connections; port 1883 is plain and restricted to local dev / simulator.
- API enforces API-key authentication with JWT helper utilities.
- All Python services validate configuration via Pydantic models.
- `/healthz` endpoints and structured JSON logging across all services.

## Local Development

- Copy `.env.example` files and fill in secrets before starting services.
- Provide Mosquitto password file and TLS certificates before using port 8883.
- Use `docker compose logs -f <service>` for per-service log tailing.
