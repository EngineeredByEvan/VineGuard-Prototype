# VineGuard Gateway Integration Guide

**Last updated:** 2026-04-27  
**Component:** `edge/gateway` — `vineguard_gateway` Python package  
**Version:** matches gateway `pyproject.toml`

---

## 1. Overview

The VineGuard gateway is a typed Python service that bridges LoRa telemetry
from field nodes to the cloud MQTT broker. It sits between the radio layer and
the cloud ingestor, and is responsible for:

- Receiving raw payloads from nodes (serial USB, ChirpStack MQTT, or mock)
- Decoding all payload formats (V1 JSON, compact P2P JSON, VGPP-1 binary,
  legacy camelCase) into the canonical V1 format
- Validating decoded payloads against range constraints before publishing
- Publishing validated payloads to the cloud MQTT broker over TLS with QoS 1
- Buffering messages to a local JSONL file when the broker is unreachable
- Exposing a health HTTP endpoint for container orchestration probes

### Deployment targets

The gateway runs on any Linux host with Python 3.11+:

| Target | Use case |
|--------|----------|
| **Raspberry Pi** (3B+, 4, or 5) | Primary recommended field gateway; low power, GPIO for future expansion |
| **Linux mini-PC** (e.g. Intel NUC, Atomic Pi) | Higher performance; suitable when running additional local services |
| **Docker on a local server** | Lab or staging deployments; also used for the demo stack |
| **Docker Compose (cloud/infrastructure)** | Development and CI; uses `LORA_MODE=mock` |

---

## 2. Gateway Modes

The gateway's receive path is selected by the `LORA_MODE` environment variable.

| `LORA_MODE` value | Description | When to use |
|-------------------|-------------|-------------|
| `mock` | Generates synthetic V1 payloads from three built-in scenarios (basic healthy, low moisture, precision+ mildew risk). No hardware required. | Development, CI, integration testing, dashboard demos |
| `serial_json` | Reads `VGPAYLOAD:<json>` lines from a USB serial port. The node must be connected via USB (Heltec V3 has a built-in USB-Serial bridge). Firmware must be built with `BUILD_MODE_LORA_P2P`. | Field deployments where a LoRa P2P node relays to a wired gateway; also used for first-node bench testing |
| `serial_binary` | Reads raw VGPP-1 binary frames (starting with `0xA1`) from USB serial. Firmware must be built with `BUILD_MODE_LORAWAN_OTAA` and `PAYLOAD_FORMAT=BINARY`. | Bandwidth-constrained links; future direct UART connection to a LoRa concentrator module |
| `chirpstack_mqtt` | Subscribes to a ChirpStack v4 application MQTT topic. **This is a stub implementation** — see §8 for configuration requirements. | LoRaWAN deployments with a ChirpStack network server; requires significant deployment-specific setup |

---

## 3. Environment Configuration

The gateway is configured entirely through environment variables (loaded from
`.env` by `python-dotenv`). Copy `edge/gateway/.env.example` to
`edge/gateway/.env` and fill in real values.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ENVIRONMENT` | `development` | No | `development`, `production`, or `test`. Controls log level (DEBUG in dev, INFO in prod) |
| `LORA_MODE` | `mock` | No | Receive mode — see §2 for values |
| `LORA_SERIAL_PORT` | `/dev/ttyUSB0` | For serial modes | Serial port path. On Linux: `/dev/ttyUSB0`, `/dev/ttyACM0`. On Windows: `COM3`, etc. |
| `LORA_BAUD_RATE` | `115200` | No | Must match the firmware `monitor_speed` setting (default 115200 in all current firmware environments) |
| `MQTT_HOST` | _(none)_ | **Yes** | MQTT broker hostname or IP address |
| `MQTT_PORT` | `8883` | No | MQTT broker port. Use `8883` for TLS (production), `1883` for plain (local dev only) |
| `MQTT_TOPIC` | `vineguard/telemetry` | No | Topic to publish telemetry messages on. Must match the ingestor's subscription topic |
| `MQTT_USERNAME` | _(none)_ | **Yes** | MQTT username. Use a publish-only account — see §5 and provisioning security notes |
| `MQTT_PASSWORD` | _(none)_ | **Yes** | MQTT password. Never commit this value |
| `CA_CERT_PATH` | _(none)_ | **Yes** | Path to the CA certificate PEM file for TLS broker verification |
| `CLIENT_CERT_PATH` | _(empty)_ | No | Path to the client certificate PEM for mutual TLS (mTLS). Leave empty for server-only TLS |
| `CLIENT_KEY_PATH` | _(empty)_ | No | Path to the client private key PEM for mTLS. Leave empty for server-only TLS |
| `OFFLINE_CACHE_PATH` | `./data/offline-cache.jsonl` | No | Path to the JSONL file used to buffer messages when the broker is unreachable. Parent directory is created automatically |
| `HEALTH_PORT` | `8080` | No | TCP port for the HTTP health endpoint (`GET /healthz`) |
| `GATEWAY_ID` | `vg-gw-001` | No | String identifier injected into every outgoing payload as `gateway_id`. Use a unique value per physical gateway |

---

## 4. Serial / LoRa Receiver Hardware Setup

### 4.1 serial_json mode (Heltec V3 via USB)

In this configuration a single LoRa P2P node is connected directly to the
gateway host by USB. This is common for bench testing and for small single-node
deployments where the gateway and node are co-located.

1. Connect the Heltec WiFi LoRa 32 V3 to the gateway host via USB-C.
2. The on-board CP2102 (or CH340) USB-Serial bridge enumerates automatically
   on Linux.
3. Identify the port:

   ```bash
   # Linux — list USB serial devices
   ls /dev/ttyUSB*
   ls /dev/ttyACM*

   # Or use udevadm to confirm the device
   udevadm info --name=/dev/ttyUSB0 | grep -i product
   ```

4. Set `LORA_SERIAL_PORT=/dev/ttyUSB0` (or the detected path) in `.env`.
5. Set `LORA_BAUD_RATE=115200`.

**Windows:** Open Device Manager, expand "Ports (COM & LPT)", and note the
`COMx` number assigned to the Heltec. Set `LORA_SERIAL_PORT=COM3` (or your
port number).

**Linux serial port permissions:** By default, serial ports on Linux are owned
by the `dialout` group. Add your user to this group to avoid running the gateway
as root:

```bash
sudo usermod -aG dialout $USER
# Log out and back in (or run: newgrp dialout) for the change to take effect
```

### 4.2 serial_binary mode

Configure the serial port identically to §4.1. The difference is in the
firmware: the node must be flashed with `BUILD_MODE_LORAWAN_OTAA` and
`PAYLOAD_FORMAT=PAYLOAD_FMT_BINARY`. The gateway detects the `0xA1` magic byte
and applies binary frame parsing with CRC verification.

### 4.3 LoRa concentrator (future)

Direct connection to a LoRa concentrator module (e.g., RAK2287, SX1302-based
HAT for Raspberry Pi) is not yet implemented in the gateway. When added, it
will appear as a new `LORA_MODE` value. For now, use `serial_json` with an
intermediate LoRa P2P relay node.

---

## 5. MQTT TLS Configuration

Production deployments must use TLS on port 8883. Plain port 1883 is only
acceptable on a loopback interface during local development.

### 5.1 Obtaining the CA certificate

**Self-signed CA (demo/lab):** Generate a self-signed CA and broker certificate:

```bash
# Create CA key and certificate
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=VineGuard-CA"

# Create broker key and CSR
openssl genrsa -out broker.key 2048
openssl req -new -key broker.key -out broker.csr \
    -subj "/CN=mqtt.vineguard.local"

# Sign the broker cert with the CA
openssl x509 -req -days 3650 -in broker.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial -out broker.crt

# Copy CA cert to the gateway certs directory
cp ca.crt edge/gateway/certs/ca.crt
```

**Cloud-managed CA (production):** Use the CA bundle from your cloud MQTT
provider (e.g., AWS IoT Core, HiveMQ Cloud). Download it and set `CA_CERT_PATH`
to the file path on the gateway host.

### 5.2 Testing TLS connectivity with mosquitto_pub

```bash
mosquitto_pub \
    -h YOUR_BROKER_HOST -p 8883 \
    --cafile /path/to/ca.crt \
    -u gateway_publisher -P your_password \
    -t vineguard/test -m "ping" -d
# Expected: ... rc=0 (MQTT_ERR_SUCCESS)
```

### 5.3 Mutual TLS (mTLS)

To require client certificates (recommended for production):

1. Generate a client certificate signed by the same CA.
2. Set `CLIENT_CERT_PATH` and `CLIENT_KEY_PATH` in `.env`.
3. Configure Mosquitto with `require_certificate true` in `mosquitto.conf`.

---

## 6. Offline Cache

When the MQTT broker is unreachable, the gateway writes validated payloads to a
JSONL (newline-delimited JSON) file rather than dropping them.

### 6.1 File location

Controlled by `OFFLINE_CACHE_PATH` (default: `./data/offline-cache.jsonl`).
Each line is a complete V1 JSON payload. The file is created automatically when
the first message is cached; the parent directory is also created if absent.

### 6.2 Drain behaviour

At the start of every 5-second poll cycle the gateway calls
`OfflineCache.drain()`:

1. If the cache file exists, read all lines into memory.
2. Delete the cache file.
3. Attempt to publish the cached messages through the normal publish path
   (with exponential-backoff retry, up to 5 attempts).
4. If the broker is still unreachable, the messages are written back to the
   cache file.

This means the cache operates atomically: either all messages in a drain cycle
are published or they are all re-cached. There is no partial-drain state.

### 6.3 If the cache grows too large

If the broker is permanently down (e.g., a multi-day network outage), the cache
file will grow continuously. To manage this:

- Monitor file size with an OS-level alert (cron job or Prometheus
  `node_exporter` disk metric).
- If the file exceeds an acceptable threshold (e.g., 100 MB), archive the
  oldest lines manually before the gateway next starts.
- Stop the gateway, truncate or rotate the file, then restart.

---

## 7. Health Endpoint

The gateway exposes a lightweight HTTP health endpoint for container
orchestration liveness probing.

### 7.1 Response

```
GET http://<host>:<HEALTH_PORT>/healthz
```

Success response (HTTP 200):

```json
{"status": "ok", "service": "vineguard-gateway"}
```

Any other path returns HTTP 404. The endpoint does not check broker
connectivity — it only confirms the process is alive.

### 7.2 Docker healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:8080/healthz || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### 7.3 Kubernetes liveness probe

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3
```

---

## 8. ChirpStack LoRaWAN Integration

> **Important:** The `chirpstack_mqtt` gateway mode is a **stub**. The MQTT
> subscription and message callback logic is not yet implemented. This section
> documents the intended integration. Completing it requires deployment-specific
> ChirpStack configuration.

### 8.1 Overview

ChirpStack (v4) is the LoRaWAN network server. Field nodes perform OTAA joins
through a LoRa concentrator connected to a UDP packet forwarder. ChirpStack
publishes decoded uplink payloads to an MQTT broker; the VineGuard gateway
subscribes to that topic and processes the messages.

### 8.2 ChirpStack configuration checklist

1. **Create an Application** in the ChirpStack web UI. Note the numeric
   Application ID (e.g., `1`).

2. **Create a Device Profile:**
   - Region: `US915`
   - Sub-band: **Sub-band 2** (channels 8–15 + 65) — the most widely supported
     sub-band; matches the `LORAWAN_SUBBAND 2` constant in `build_config.h`
   - MAC version: LoRaWAN 1.0.4 (or 1.1.0 if your network server supports it)
   - Activation mode: **OTAA**

3. **Register each device** with its DevEUI, AppEUI (JoinEUI), and AppKey from
   `provisioning_manifest.csv` (see `docs/PROVISIONING.md`).

4. **Configure the payload codec** (JavaScript codec in ChirpStack Application):
   - If firmware uses `PAYLOAD_FMT_BINARY`: the codec must decode a VGPP-1
     binary frame (see `docs/PAYLOAD_CONTRACT.md §4`) and output a compact JSON
     object using the abbreviated key map (`sm`, `at`, `ah`, `p`, `l`, etc.).
   - If no codec is configured, ChirpStack publishes the raw `FRMPayload` as
     base64 in the `data` field. The current stub does not handle this case.

5. **MQTT topic format** (ChirpStack v4):

   ```
   application/{application_id}/device/{dev_eui}/event/up
   ```

   To receive all devices in an application the gateway should subscribe to:

   ```
   application/1/device/+/event/up
   ```

   The `dev_eui` in the topic path must be mapped to a `device_id` using a
   lookup table (from provisioning manifest or database query).

### 8.3 Steps to complete the stub

When implementing `_ChirpStackMqttLoRa`:

1. In `open()`: connect a `paho.mqtt.client` subscriber to the ChirpStack MQTT
   broker and subscribe to the wildcard uplink topic.
2. In the on-message callback: extract `devEUI` from the topic path, look up
   the corresponding `device_id`, decode the `object` field (codec output) or
   `data` (base64 raw), and append a `LoRaMessage` to `self._pending`.
3. Populate `rssi` and `snr` from the `rxInfo[0]` object in the uplink JSON.
4. Surface the ChirpStack application ID as a new environment variable
   (`CHIRPSTACK_APP_ID`) and document it in §3.

---

## 9. Running the Gateway

### 9.1 Directly with Python

```bash
cd edge/gateway
pip install -e .

cp .env.example .env
# Edit .env: set MQTT_HOST, MQTT_USERNAME, MQTT_PASSWORD, CA_CERT_PATH, etc.

python -m vineguard_gateway.main
```

Or use the installed console script:

```bash
vineguard-gateway
```

### 9.2 With Docker Compose

The production cloud stack (`cloud/infrastructure/docker-compose.yml`) does not
include the gateway (it runs on the field edge device, not in the cloud). For
local integration testing, add a gateway service to a local compose override:

```yaml
# docker-compose.override.yml (not committed)
services:
  gateway:
    build:
      context: ../../edge/gateway
    env_file:
      - ../../edge/gateway/.env
    depends_on:
      mqtt:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 9.3 As a systemd service (Raspberry Pi / Linux)

```ini
# /etc/systemd/system/vineguard-gateway.service
[Unit]
Description=VineGuard LoRa Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vineguard
WorkingDirectory=/opt/vineguard/edge/gateway
EnvironmentFile=/opt/vineguard/edge/gateway/.env
ExecStart=/opt/vineguard/.venv/bin/python -m vineguard_gateway.main
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vineguard-gateway
sudo journalctl -u vineguard-gateway -f
```

---

## 10. Structured Log Format

The gateway uses `loguru` for structured logging. Key log events and their
format (timestamp format: `HH:MM:SS`):

### Startup

```
12:00:00 | INFO     | === VineGuard Gateway starting (mode=serial_json, env=production) ===
12:00:00 | INFO     | Health endpoint listening on :8080/healthz
12:00:00 | INFO     | LoRa mode: serial_json on /dev/ttyUSB0 @ 115200 baud
12:00:00 | INFO     | Connecting to MQTT broker.vineguard.local:8883
12:00:00 | INFO     | Gateway ready – polling every 5 s
```

### Message received and decoded

```
12:00:05 | DEBUG    | Serial RX: VGPAYLOAD:{"v":"1.0","id":"vg-node-001",...}
12:00:05 | INFO     | Decoded serial_json payload from vg-node-001
```

### Payload validated and published

```
12:00:05 | INFO     | Payload validated: device=vg-node-001 tier=basic soil=28.4 T=21.3
12:00:05 | INFO     | Published: topic=vineguard/telemetry device=vg-node-001 seq=42
12:00:05 | INFO     | Published 1 message(s) to vineguard/telemetry
```

### Decode failure (payload dropped)

```
12:00:10 | WARNING  | Decode error (skipping): CRC mismatch: stored=0x1234 calc=0xABCD
12:00:10 | WARNING  | Payload validation failed (soil_moisture_pct=150 out of range [0, 100]), dropping: device=vg-node-001
```

### Offline cache events

```
12:05:00 | ERROR    | Publish failed after retries: [Errno 111] Connection refused — caching 3 messages
12:05:00 | WARNING  | Cached message offline (device=vg-node-001)
12:10:00 | INFO     | Draining 5 cached messages
12:10:00 | INFO     | Drained 5 cached messages from ./data/offline-cache.jsonl
```

### ChirpStack stub warning

```
12:00:00 | WARNING  | LoRa mode: chirpstack_mqtt — stub implementation. Configure ChirpStack MQTT broker and topic in environment. See docs/GATEWAY_INTEGRATION.md.
```

---

## 11. Troubleshooting

### Wrong baud rate

**Symptom:** Serial data is received but every line produces
`Decode error: Not valid JSON` or shows garbled characters.

**Fix:** Confirm `LORA_BAUD_RATE` matches the firmware `monitor_speed`. All
current PlatformIO environments default to `115200`. Check `platformio.ini`.

```bash
# Quick check: view raw serial at 115200
stty -F /dev/ttyUSB0 115200 raw && cat /dev/ttyUSB0
# Readable VGPAYLOAD: lines confirm the baud rate is correct
```

### Serial port permission denied

**Symptom:** Gateway exits with:
`Cannot open serial port /dev/ttyUSB0: [Errno 13] Permission denied`

**Fix:** Add the gateway user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
newgrp dialout   # apply without full logout
```

Or create a persistent udev rule:

```
# /etc/udev/rules.d/99-vineguard.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", \
    MODE="0666", SYMLINK+="vineguard-node"
```

Reload: `sudo udevadm control --reload && sudo udevadm trigger`

### MQTT TLS certificate mismatch

**Symptom:** Gateway logs `SSL: CERTIFICATE_VERIFY_FAILED` or
`hostname mismatch` on connect.

**Fixes:**

1. Verify `CA_CERT_PATH` points to the CA that signed the broker certificate
   (not the broker certificate itself).
2. Confirm `MQTT_HOST` matches the `CN` or a `SAN` entry in the broker
   certificate. An IP address in `MQTT_HOST` requires the cert to include that
   IP as a SAN.
3. Test in isolation with `mosquitto_pub --cafile ...` (see §5.2) to separate
   the TLS issue from the gateway process.

### MQTT connection succeeds but publishes are rejected

**Symptom:** Gateway connects without error but messages never appear in the
ingestor; `MQTT publish failed` in logs.

**Fixes:**

1. Check the MQTT user (`MQTT_USERNAME`) has write permission on
   `vineguard/telemetry` in the Mosquitto ACL file
   (`cloud/infrastructure/mosquitto/mosquitto.conf`).
2. Verify QoS 1 acknowledgements are arriving (`result.rc == 0`). Rejected
   publishes are almost always an ACL or authentication misconfiguration.

### Offline cache never drains (broker permanently down)

**Symptom:** Cache file grows indefinitely; draining re-caches the same
messages every cycle.

**Diagnosis:**

```bash
# Check file size and line count
ls -lh ./data/offline-cache.jsonl
wc -l  ./data/offline-cache.jsonl

# Inspect the first cached payload
head -1 ./data/offline-cache.jsonl | python3 -m json.tool
```

**Fix:** Restore MQTT broker connectivity. Once the broker is reachable the
gateway will drain the backlog automatically on the next poll cycle. To
discard stale cached data without publishing:

```bash
systemctl stop vineguard-gateway
rm ./data/offline-cache.jsonl
systemctl start vineguard-gateway
```

### Node transmits but gateway sees nothing

**Symptom:** No `Serial RX:` lines in the gateway log even with
`ENVIRONMENT=development`.

**Checks:**

1. Confirm the node is powered and transmitting — connect it to a PC and run
   `pio device monitor --baud 115200` to verify `VGPAYLOAD:` lines appear.
2. Confirm `LORA_SERIAL_PORT` is set to the correct device path.
3. Ensure only one process has the port open. The PlatformIO serial monitor and
   the gateway cannot share the same port; close the monitor before starting
   the gateway.
4. Try a different USB cable — some USB-C cables are charge-only and do not
   carry data.
