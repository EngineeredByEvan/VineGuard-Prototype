# VineGuard Backend

This package bundles the FastAPI cloud API, MQTT telemetry ingestion worker, and rule-based
analytics for VineGuard prototype nodes.

## Features

- Asynchronous MQTT consumer that writes telemetry into TimescaleDB and updates node status
- FastAPI service with JWT-based authentication (access & refresh tokens) and org-level RBAC
- Rule-based insights (battery alerts, irrigation advice, sensor faults, anomalies) with clear
  TODO hooks for future ML models
- Command publishing endpoint for OTA/config downlinks
- Seed & fake telemetry utilities for local development

## Requirements

- Python 3.11+
- PostgreSQL 14+ with TimescaleDB extension enabled
- MQTT broker (e.g. Mosquitto) reachable from the services

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
cp .env.example .env
# edit .env to match your environment
```

Ensure TimescaleDB extension is installed in your target database:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

## Database bootstrap & seed data

The seed script will create the schema, convert `telemetry_raw` to a hypertable, and insert a demo
organization/site/node plus an admin user.

```bash
python -m vineguard_backend.scripts.seed_demo
```

Default login credentials:

- **Email:** `demo@vineguard.io`
- **Password:** `ChangeMe123!`

## Running the API service

```bash
uvicorn vineguard_backend.services.api:app --host 0.0.0.0 --port 8000 --reload
```

The service exposes:

- `POST /auth/login` for access & refresh tokens
- `POST /auth/refresh` to rotate tokens
- `GET /api/*` routes for telemetry, insights, and node status

## Running the telemetry ingestion worker

```bash
python -m vineguard_backend.services.telemetry_ingest
```

This process subscribes to the wildcard defined by `TELEMETRY_TOPIC_FILTER` and persists validated
messages into TimescaleDB while emitting insights.

## Generating fake telemetry

With a local MQTT broker running on `localhost:1883`, send demo payloads using:

```bash
python -m vineguard_backend.scripts.fake_telemetry --count 5 --interval 5
```

## Tests / linting

Lightweight syntax validation can be run with:

```bash
python -m compileall src
```

You can integrate `pytest` later via the optional `dev` dependencies.
