# VineGuard Cloud Prototype

This repository contains a containerized prototype of the VineGuard cloud platform. It includes services for API access, telemetry ingestion, real-time analytics, and synthetic data seeding to showcase end-to-end vineyard monitoring.

## Stack overview

The `/cloud` directory hosts all infrastructure and service definitions:

- **TimescaleDB (Postgres)** – primary storage for telemetry, insights, and metadata with hypertable configuration.
- **Redis** – lightweight message bus for pushing live telemetry and insights to dashboards.
- **EMQX MQTT broker** – gateway for sensor telemetry and outbound commands.
- **API service** – FastAPI application exposing authentication, REST, command, and live streaming endpoints.
- **Ingestor** – Python worker that subscribes to telemetry topics, validates payloads, persists data, and pushes live updates.
- **Analytics worker** – Streaming and batch analytics that emit rule-based and statistical insights.
- **Seed service** – Bootstraps a demo tenant and continuously publishes synthetic telemetry for evaluation.

## Getting started

1. Copy the sample environment configuration and adjust secrets if needed:
   ```bash
   cp cloud/.env.example cloud/services/api/.env
   cp cloud/.env.example cloud/services/ingestor/.env
   cp cloud/.env.example cloud/services/analytics/.env
   cp cloud/.env.example cloud/services/seed/.env
   ```
   Each service only reads the variables it needs; feel free to trim the files.

2. Launch the complete stack:
   ```bash
   cd cloud/infrastructure
   docker compose up -d --build
   ```

3. Confirm the API is healthy and view automatic documentation:
   ```bash
   curl http://localhost:8000/
   ```
   OpenAPI docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Smoke tests

1. **Register and authenticate** – Use the HTTP collections in `cloud/docs/*.http` or run:
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "owner@example.com", "password": "changeme123", "org_name": "Orchard"}'
   ```
   Alternatively, sign in with the seeded demo account:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "demo@vineguard.io", "password": "demo1234"}'
   ```

2. **Inspect nodes and telemetry** – After logging in, use the access token:
   ```bash
   curl http://localhost:8000/nodes \
     -H "Authorization: Bearer <access-token>"

   curl "http://localhost:8000/nodes/<node-id>/telemetry?limit=10" \
     -H "Authorization: Bearer <access-token>"
   ```

3. **Check insights** – Rule-based and batch analytics will populate the `insights` table:
   ```bash
   curl http://localhost:8000/insights \
     -H "Authorization: Bearer <access-token>"
   ```

4. **Live stream** – Subscribe to server-sent events to watch telemetry and insights in real time (requires a tool like `curl` or `httpie`):
   ```bash
   curl -H "Accept: text/event-stream" \
        -H "Authorization: Bearer <access-token>" \
        http://localhost:8000/live/<org-id>
   ```

5. **Send a command** – Publish outbound commands to sensors via MQTT through the API:
   ```bash
   curl -X POST http://localhost:8000/commands \
     -H "Authorization: Bearer <access-token>" \
     -H "Content-Type: application/json" \
     -d '{"node_id": "<node-id>", "command": "irrigate", "payload": {"duration_minutes": 10}}'
   ```

## Database schema & migrations

`cloud/infrastructure/db/init/001_init.sql` initializes TimescaleDB, creates the hypertable-backed `telemetry_raw` table, and defines relational tables for organizations, users, nodes, status snapshots, and insights. The file is mounted into the TimescaleDB container to run automatically at startup.

## Synthetic telemetry

The seed service provisions a demo organization/site/node and uses MQTT to publish telemetry every five seconds. Payloads include battery, temperature, and moisture metrics to exercise ingestion and analytics pipelines.

## Project layout

```
cloud/
  infrastructure/
    docker-compose.yml
    db/init/001_init.sql
  services/
    api/
    ingestor/
    analytics/
    seed/
  docs/
    auth.http
    nodes.http
```

## Stopping services

Shut down the stack with:
```bash
docker compose down
```
from inside `cloud/infrastructure`.

## Troubleshooting

- Verify the TimescaleDB container is healthy before the API starts. `docker compose ps` shows service status.
- Use `docker compose logs -f <service>` to inspect ingestion or analytics workers.
- Ensure ports 5432, 6379, 1883, and 8000 are available on your host.
