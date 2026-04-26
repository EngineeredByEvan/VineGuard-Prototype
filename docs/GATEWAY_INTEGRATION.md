# Gateway Integration

## Modes
- `mock`: internal generated v1 telemetry.
- `serial_json`: read JSON lines from serial, normalize, publish MQTT.
- `serial_binary`: read compact binary packet, decode + normalize.
- `chirpstack_mqtt`: reserved for deployment-specific integration.

## Env vars
`LORA_MODE, LORA_SERIAL_PORT, LORA_BAUD_RATE, MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD, CA_CERT_PATH, CLIENT_CERT_PATH, CLIENT_KEY_PATH, OFFLINE_CACHE_PATH, HEALTH_PORT`

## Resilience
- QoS1 publish.
- Exponential retry in main loop.
- JSONL offline cache append + drain.
- `/healthz` endpoint.
