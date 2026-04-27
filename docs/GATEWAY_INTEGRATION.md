# VineGuard Gateway Integration Guide

## Overview

The VineGuard gateway bridges LoRa/serial telemetry from sensor nodes to the MQTT broker consumed by the cloud ingestor. It runs as a Python process on a local Linux computer (Raspberry Pi, mini-PC, or Docker host) within LoRa range of the field nodes.

```
[ESP32 Node] ──LoRa/USB──▶ [Gateway Process] ──MQTT TLS──▶ [Cloud Broker]
                              ↕ JSONL cache                    ↓
                              (offline buffer)            [Ingestor] → DB
```

The gateway is located at `edge/gateway/`. It is a standalone Python package managed by `pyproject.toml`.

---

## Gateway Modes

Set `LORA_MODE` in `.env` to select the receive mode:

| LORA_MODE | Description | When to use |
|-----------|-------------|-------------|
| `mock` | Generates synthetic V1 payloads cycling through 3 scenarios | Development, CI, demos without hardware |
| `serial_json` | Reads `VGPAYLOAD:<json>` lines from USB serial | Node connected via USB, or node running `lora_p2p` build with USB serial |
| `serial_binary` | Reads raw VGPP-1 binary frames from USB serial | Future; binary LoRa P2P mode |
| `chirpstack_mqtt` | Subscribes to ChirpStack application MQTT topic | Full LoRaWAN deployment with ChirpStack network server (stub) |

For the **MVP with LoRa P2P nodes**, use `serial_json`.

For the **demo/development environment** without any hardware, use `mock`.

---

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Runtime environment (development | production | test)
ENVIRONMENT=production

# LoRa receive mode
LORA_MODE=serial_json

# Serial port for serial_json / serial_binary modes
# Linux: /dev/ttyUSB0 or /dev/ttyACM0
# macOS: /dev/cu.usbserial-*
# Windows: COM3
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_BAUD_RATE=115200       # must match firmware monitor_speed

# MQTT broker
MQTT_HOST=mqtt.vineguard.local
MQTT_PORT=8883              # TLS port (use 1883 for non-TLS dev broker)
MQTT_TOPIC=vineguard/telemetry
MQTT_USERNAME=gateway_publisher
MQTT_PASSWORD=<generate a strong password>

# TLS certificates (required for port 8883)
CA_CERT_PATH=certs/ca.crt
CLIENT_CERT_PATH=            # leave empty for server-only TLS
CLIENT_KEY_PATH=             # leave empty for server-only TLS

# Offline cache (buffers payloads when broker is unreachable)
OFFLINE_CACHE_PATH=./data/offline-cache.jsonl

# Health probe port
HEALTH_PORT=8080

# Gateway identity (injected into published payloads as gateway_id)
GATEWAY_ID=vg-gw-001
```

**Production security checklist:**
- `MQTT_PASSWORD` must be a random string ≥ 16 characters.
- `.env` must be chmod 600 and owned by the gateway process user.
- Never commit `.env` to git.
- The gateway MQTT user should have **publish-only** ACL on `vineguard/telemetry`.

---

## Running the Gateway

### Directly (development)
```bash
cd edge/gateway
pip install -e ".[dev]"
cp .env.example .env
# edit .env
python -m vineguard_gateway.main
```

### Docker Compose (production)
The gateway is included in `cloud/infrastructure/docker-compose.yml`. It starts automatically with:
```bash
docker compose up gateway
```

Override environment variables in `docker-compose.yml` or via a `.env` file in `cloud/infrastructure/`.

### Systemd service (Raspberry Pi)
```ini
[Unit]
Description=VineGuard LoRa Gateway
After=network.target

[Service]
User=vineguard
WorkingDirectory=/opt/vineguard-gateway
ExecStart=/opt/vineguard-gateway/.venv/bin/python -m vineguard_gateway.main
EnvironmentFile=/opt/vineguard-gateway/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Serial / LoRa Receiver Hardware Setup

### serial_json mode (USB serial from node)

1. Connect the node to the Raspberry Pi via USB-C cable.
2. Identify the port:
   - Linux: `ls /dev/ttyUSB* /dev/ttyACM*`
   - macOS: `ls /dev/cu.*`
   - Windows: Device Manager → Ports (COM & LPT)
3. Add the gateway user to the `dialout` group (Linux):
   ```bash
   sudo usermod -a -G dialout vineguard
   # Log out and back in for change to take effect
   ```
4. Set `LORA_SERIAL_PORT=/dev/ttyUSB0` (or the correct port) in `.env`.
5. Set `LORA_BAUD_RATE=115200` (must match firmware `monitor_speed`).

The firmware emits lines in the format: `VGPAYLOAD:{...json...}\r\n`

The gateway's `_SerialJsonLoRa` class reads `in_waiting` bytes every 5 seconds, strips the `VGPAYLOAD:` prefix, and passes the JSON to `decoder.decode_auto()`.

### LoRa concentrator (future)

For a true LoRa P2P receive setup without USB, a LoRa module (SX1262 or SX1276) attached to the Raspberry Pi SPI bus can listen for transmissions from field nodes. This mode is not yet implemented. The `serial_binary` mode provides the decode path; a future `serial_lora_rx` receive driver needs to be added to `lora.py`.

---

## MQTT TLS Configuration

### Server-only TLS (most common)

Obtain the broker's CA certificate (`ca.crt`) and set `CA_CERT_PATH=certs/ca.crt`.

Test connectivity:
```bash
mosquitto_pub -h mqtt.vineguard.local -p 8883 \
  --cafile certs/ca.crt \
  -u gateway_publisher -P <password> \
  -t vineguard/telemetry -m '{"test":true}' -d
```

### Mutual TLS (optional)

Set `CLIENT_CERT_PATH` and `CLIENT_KEY_PATH` to the gateway's certificate and private key. The broker must be configured to require client certificates on port 8883.

### Self-signed CA for development

```bash
# Generate CA key and cert
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/CN=VineGuard Dev CA"

# Generate broker key and cert
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=mqtt.local"
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt

# Copy ca.crt to gateway certs/ directory
```

Place generated certs in `cloud/infrastructure/mosquitto/certs/` (they are gitignored).

---

## Offline Cache

The offline cache (`OFFLINE_CACHE_PATH`) is a JSONL file that buffers payloads when the MQTT broker is unreachable.

- **Append**: called when publish fails after all retries.
- **Drain**: at the start of each 5-second poll cycle, all cached messages are loaded and re-published.
- **Persistence**: the JSONL file survives process restarts; payloads buffer across gateway reboots.
- **File growth**: each payload is ~300–500 bytes JSON. At 15-min intervals, 24 hours of data = ~96 payloads × 400 bytes ≈ 38 KB. The file is deleted after successful drain.

If the cache grows unexpectedly (broker permanently unreachable), it will never auto-prune. Monitor the file size:
```bash
ls -lh data/offline-cache.jsonl
wc -l data/offline-cache.jsonl
```

---

## Health Endpoint

The gateway exposes a lightweight HTTP health probe at `http://0.0.0.0:<HEALTH_PORT>/healthz`:

```
GET /healthz  →  200 {"status":"ok","service":"vineguard-gateway"}
```

**Docker Compose healthcheck:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
  interval: 30s
  timeout: 5s
  retries: 3
```

**Kubernetes liveness probe:**
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
```

---

## ChirpStack LoRaWAN Integration (Stub)

`LORA_MODE=chirpstack_mqtt` is a **stub** in the current implementation. To complete it:

1. **Deploy ChirpStack v4** with a LoRa concentrator (e.g. RAK7258, Dragino LPS8) connected to your network.
2. **Create a ChirpStack application** for VineGuard nodes.
3. **Create a device profile** for US915, OTAA, Class A.
4. **Configure US915 sub-band 2** (enabled channels 8–15, 64–71) in the gateway/network server configuration.
5. **Register each device** using the DevEUI, AppEUI, and AppKey from the provisioning manifest.
6. **Add payload codec** (optional but recommended): add a JavaScript codec in ChirpStack that decodes the VGPP-1 binary frame into a JSON object. The Python `decode_payload.py` tool can serve as a reference.
7. **MQTT integration**: ChirpStack publishes uplinks to MQTT. Enable the MQTT integration in ChirpStack's application settings. The topic format is:
   ```
   application/{application_id}/device/{dev_eui}/event/up
   ```
8. **Update `_ChirpStackMqttLoRa`** in `lora.py`:
   - Subscribe to the ChirpStack MQTT topic.
   - Extract the `data` field (base64-encoded payload) or the decoded object.
   - Pass to `decoder.decode_auto()`.

---

## Structured Log Events

| Log message | Level | Meaning |
|------------|-------|---------|
| `LoRa mode: serial_json on /dev/ttyUSB0 @ 115200 baud` | INFO | Serial port opened successfully |
| `Decoded serial_json payload from vg-node-001` | INFO | Compact JSON decoded |
| `Payload validated: device=vg-001 tier=basic soil=28.4 T=21.3` | INFO | Passed validation, ready to publish |
| `Payload validation failed (device_id too short), dropping: device=ab` | WARNING | Rejected payload |
| `Decode error (skipping): JSON parse error: ...` | WARNING | Malformed line from serial |
| `Published: topic=vineguard/telemetry device=vg-001 seq=42` | INFO | MQTT publish succeeded |
| `Cached message offline (device=vg-001)` | WARNING | Broker unreachable, payload buffered |
| `Drained 3 cached messages from ./data/offline-cache.jsonl` | INFO | Cache drain succeeded |
| `Publish failed after retries: ... — caching N messages` | ERROR | Broker down, all messages cached |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Cannot open serial port /dev/ttyUSB0` | Wrong port or permissions | `ls /dev/ttyUSB*`, add user to `dialout`, check USB cable |
| `Decode error: JSON parse error` | Node firmware printing debug lines before VGPAYLOAD | Normal; non-VGPAYLOAD lines are ignored |
| `Decode error: Not valid JSON` | Node crashing mid-print | Check node power supply, inspect serial log for exceptions |
| `MQTT publish failed: [Errno 111] Connection refused` | Broker not running or wrong host/port | Check `MQTT_HOST`/`MQTT_PORT`, test with `mosquitto_pub` |
| `MQTT TLS handshake error` | CA cert mismatch or expired | Verify `CA_CERT_PATH` points to the correct CA cert for your broker |
| `Payload validation failed: device_id length invalid` | Provisioning not done | Flash with correct lorawan_keys.h, check NVS device_id |
| Cache file growing without draining | Broker permanently unreachable | Fix broker connectivity; manually clear cache with `rm ./data/offline-cache.jsonl` after broker is restored |
