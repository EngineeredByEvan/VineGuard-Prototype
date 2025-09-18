# VineGuard™ Cloud API

FastAPI-based service providing REST + SSE telemetry access, authentication, and
integration with TimescaleDB and Redis.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

Ensure Postgres/TimescaleDB and Redis are available; `docker-compose` in
`cloud/infrastructure` provisions these for local development.
