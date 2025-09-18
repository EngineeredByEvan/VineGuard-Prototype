# VineGuard Prototype

End-to-end prototype for ingesting MQTT telemetry from VineGuard field nodes, persisting to
TimescaleDB, emitting agronomic insights, and visualizing via a web dashboard.

## Repository layout

- `backend/` — FastAPI cloud API, MQTT ingestion worker, analytics rules, and seed utilities
- `dashboard/` — React + Vite single-page application for monitoring telemetry & insights

Each package ships with its own README detailing prerequisites, setup, and run commands. Refer to
`.env.example` in each directory to configure environment variables.

## Quick start

1. Provision PostgreSQL with TimescaleDB and an MQTT broker (e.g. Mosquitto).
2. Follow `backend/README.md` to install dependencies, configure `.env`, and run the seed script.
3. Start the API server (`uvicorn …`) and the telemetry ingestion worker.
4. Optionally send demo telemetry via `python -m vineguard_backend.scripts.fake_telemetry`.
5. Follow `dashboard/README.md` to install dependencies and run `npm run dev`.

The dashboard authenticates against the backend using JWT (access + refresh) and continuously polls
for node status, latest sensors, and rule-based insights.
