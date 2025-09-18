# ADR-001: VineGuard Platform Foundations

## Status
Accepted

## Context

VineGuard requires an end-to-end telemetry platform spanning embedded nodes,
edge gateways, cloud ingestion, analytics, and a real-time dashboard. Core
requirements include secure transport (LoRa -> MQTT over TLS), typed codebases,
clear module boundaries, and operational readiness.

## Decision

- **Firmware** uses PlatformIO/Arduino for ESP32 with FreeRTOS tasks to balance
  low-power telemetry and OTA updates.
- **Edge gateway** implemented in Python 3.11 with Pydantic validation, Loguru
  logging, offline buffering, and TLS MQTT publishing.
- **Cloud** stack built on FastAPI, TimescaleDB, Redis, MQTT broker, ingestion
  worker, and analytics scheduler orchestrated by Docker Compose.
- **Web dashboard** uses Vite + React + Tailwind with SSE streaming and charts.
- Configuration managed via `.env` files adhering to 12-factor app principles.

## Consequences

- Enables local reproduction via `docker compose up -d` and `npm run dev`.
- Each service can evolve independently with clear contracts (MQTT payloads,
  REST/SSE endpoints, Postgres schema).
- TLS certificates and credentials must be provisioned for Mosquitto and shared
  securely with edge/ingestor services.
