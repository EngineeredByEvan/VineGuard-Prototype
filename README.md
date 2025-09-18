# VineGuard™ Prototype

VineGuard is a smart viticulture IoT platform spanning edge firmware, gateway
bridge, cloud ingestion/analytics, and a modern web dashboard.

```
/vineguard
  /firmware/esp32-node          # ESP32 (Arduino/FreeRTOS) telemetry firmware
  /edge/gateway                 # Python LoRa <-> MQTT bridge
  /cloud                        # FastAPI + TimescaleDB stack with analytics
  /web                          # React + TypeScript dashboard
  /docs                         # Architecture docs, ADRs, API samples
```

## Quickstart

### Cloud stack

```bash
cd cloud/infrastructure
docker compose up -d --build
```

- TimescaleDB + Timescale extension
- Redis for pub/sub streaming
- TLS-secured Mosquitto MQTT broker (provide certs under `mosquitto/certs`)
- FastAPI API (http://localhost:8000)
- MQTT ingestor worker
- Analytics scheduler

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
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
vineguard-gateway
```

### Firmware

Use PlatformIO in `firmware/esp32-node` for ESP32 nodes. Replace stubbed sensor
logic with hardware drivers, configure LoRaWAN stack, and provide secure OTA.

## Security & Observability

- MQTT is TLS-enabled with dedicated least-privilege credentials.
- API enforces API-key auth (with JWT helper utilities ready in config).
- All Python services validate configuration via Pydantic models.
- `/healthz` endpoints and structured logging across services.

## Local Development Notes

- Update `.env.example` copies with secrets/DSNs before running services.
- Provide Mosquitto password file and certificates prior to compose up.
- Use `docker compose logs -f api` etc. for observability while running.
