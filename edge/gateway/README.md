# VineGuard Edge Gateway

Python bridge from LoRa/serial node uplinks to MQTT for cloud ingestion.

## Features
- Gateway modes: `mock`, `serial_json`, `serial_binary`, `chirpstack_mqtt` (template).
- Payload normalization to preserve cloud compatibility:
  - legacy flat payloads
  - canonical v1 payloads (`schema_version=1.0`)
  - enhanced nested payload adapters
- QoS1 MQTT publishing, offline JSONL cache, retry/backoff, `/healthz` endpoint.

## Run
```bash
cd edge/gateway
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
vineguard-gateway
```

## Key environment variables
`LORA_MODE, LORA_SERIAL_PORT, LORA_BAUD_RATE, MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD, CA_CERT_PATH, CLIENT_CERT_PATH, CLIENT_KEY_PATH, OFFLINE_CACHE_PATH, HEALTH_PORT`
