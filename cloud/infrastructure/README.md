# VineGuard™ Cloud Infrastructure

`docker-compose.yml` orchestrates the cloud services for local development:

- TimescaleDB (PostgreSQL) with hypertable migrations and least-privilege roles
- Redis for streaming telemetry fanout
- Mosquitto MQTT broker configured for TLS
- FastAPI API service
- MQTT ingestor worker
- Analytics scheduler

## Usage

```bash
cd cloud/infrastructure
docker compose up -d --build
```

Populate `mosquitto/certs` and password file with locally generated assets.
Update the `.env.example` files per service as needed before running.
