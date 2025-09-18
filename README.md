# VineGuard Edge Gateway Prototype

This repository contains a Python 3.11 edge gateway that bridges VineGuard LoRa nodes and lab simulators to a cloud MQTT broker. The gateway normalises telemetry, enriches it with gateway metadata, buffers telemetry locally when MQTT is unavailable, and exposes observability endpoints for operations.

## Features

- LoRa (SPI) ingress with automatic simulation fallback when hardware drivers are unavailable.
- UDP JSON ingress for lab testing and CI workflows.
- Strategy-based input sources so transports can be extended independently.
- Disk-backed telemetry queue (SQLite) to survive restarts and publish data when the MQTT broker becomes reachable again.
- MQTT publishing over TLS with configuration supplied via environment variables.
- Downlink command subscription on `vineguard/{orgId}/{siteId}/{nodeId}/cmd` and routing back to the original transport.
- Structured JSON logs and a `/healthz` endpoint for observability.
- Docker and Docker Compose definitions for local development alongside an EMQX/Mosquitto-compatible broker.

## Repository Layout

```
edge/
  gateway/
    __main__.py         # Application entry point
    config.py           # Environment driven configuration
    gateway.py          # Core orchestration between sources and MQTT
    health.py           # /healthz endpoint using aiohttp
    logging_config.py   # Structured logging utilities
    mqtt_client.py      # MQTT client wrapper
    queue_store.py      # SQLite backed persistent queue
    telemetry_validator.py # Telemetry schema validation
    sources/
      base.py           # Strategy base class
      lora.py           # LoRa source with simulation fallback
      udp.py            # UDP JSON source for lab testing
simulate_node.py        # Helper script to emit UDP telemetry
requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.11+
- `pip`
- (Optional) Docker and Docker Compose for containerised workflows.

### Local Python Execution

1. Create and populate an environment file:

   ```bash
   cp .env.example .env
   ```

   Adjust the values as needed. For local testing with the included Mosquitto broker you can keep TLS disabled.

2. Install dependencies and run the gateway:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export $(grep -v '^#' .env | xargs)
   python -m edge.gateway
   ```

3. In a second terminal, simulate node traffic:

   ```bash
   python simulate_node.py --host 127.0.0.1 --port 1700 --interval 3
   ```

   The gateway will validate and enrich the telemetry before publishing it to the configured MQTT broker.

### Docker Compose

The repository includes a compose stack that runs the gateway alongside a Mosquitto broker suitable for development.

```bash
docker compose up --build
```

The gateway container exposes:

- UDP listener on port `1700`
- `/healthz` on port `8080`

To send test data while the stack is running:

```bash
python simulate_node.py --host 127.0.0.1 --port 1700 --interval 5
```

### Environment Variables

Key settings consumed by the gateway:

| Variable | Description |
| --- | --- |
| `GATEWAY_ID` | Unique identifier for the gateway appended to telemetry records. |
| `MQTT_HOST` / `MQTT_PORT` | Cloud MQTT endpoint. Compose overrides `MQTT_HOST` to the in-stack broker. |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Optional credentials. |
| `MQTT_USE_TLS` | Enable TLS (`true`/`false`). When enabled provide `MQTT_CA_CERT` and optional client certificate/key paths. |
| `MQTT_BACKOFF_BASE`, `MQTT_BACKOFF_MAX` | Exponential backoff window used when reconnecting to MQTT. |
| `QUEUE_DB_PATH` | Filesystem path for the SQLite-backed retry queue. |
| `ENABLE_UDP_SOURCE` / `ENABLE_LORA_SOURCE` | Toggle ingress sources on or off. |
| `LORA_FORCE_SIMULATION` | Force the LoRa strategy to use the built-in simulator. |
| `UDP_LISTEN_HOST` / `UDP_LISTEN_PORT` | UDP binding information. |
| `HEALTH_PORT` | Port that exposes the `/healthz` endpoint. |
| `LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, etc.). |

### Health & Observability

- Health endpoint: `http://localhost:8080/healthz`
- Logs: JSON formatted on stdout, containing metadata for each event.

### Offline Buffering Behaviour

When the MQTT broker is unavailable, telemetry messages are persisted to the SQLite queue at `QUEUE_DB_PATH`. Once connectivity is restored the gateway automatically flushes the backlog using the configured exponential backoff parameters. The queue survives restarts, ensuring telemetry continuity.

### Simulated LoRa Source

When LoRa hardware or drivers are unavailable the gateway falls back to a deterministic simulator that periodically emits sample telemetry. Disable the LoRa simulator by setting `ENABLE_LORA_SOURCE=false` or configure `LORA_FORCE_SIMULATION=false` if real hardware is expected.

## Development Tips

- Adjust the `.env` file to point at your cloud MQTT endpoint and CA certificates when testing TLS.
- The retry queue directory is mounted into the Docker container at `/data` so messages persist across restarts.
- Use the `simulate_node.py` utility to generate deterministic traffic during integration testing.

## License

This prototype is provided for demonstration purposes.
