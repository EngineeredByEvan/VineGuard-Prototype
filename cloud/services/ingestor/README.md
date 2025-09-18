# VineGuard™ MQTT Ingestor

Consumes device telemetry from the TLS MQTT broker and persists readings to
TimescaleDB while emitting live updates to Redis for streaming clients.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
vineguard-ingestor
```
