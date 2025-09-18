# VineGuard™ Edge Gateway

A typed Python service bridging LoRa telemetry from field nodes to the cloud via
TLS-secured MQTT. Designed for ruggedised gateways with intermittent
connectivity.

## Features

- Validated configuration via Pydantic models loaded from `.env`
- LoRa concentrator abstraction with offline JSONL cache for resilience
- MQTT publisher with TLS and exponential backoff retry
- `/healthz` HTTP endpoint for liveness probing

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env  # update values
vineguard-gateway
```

## Deployment Notes

- Run as a systemd service or container with mounted CA/Client certs.
- Configure the MQTT user with publish-only rights to `vineguard/telemetry`.
- Forward the health endpoint to local monitoring (Prometheus Blackbox, etc.).
