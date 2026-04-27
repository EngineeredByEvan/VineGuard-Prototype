# VineGuard ESP32 Node Firmware

Production-minded PlatformIO firmware for solar-powered vineyard sensor nodes.
Targets the **Heltec WiFi LoRa 32 V3** (ESP32-S3 + SX1262, 915 MHz).

---

## Hardware

| Component | Part | Interface |
|-----------|------|-----------|
| MCU/Radio | Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262) | — |
| Soil moisture | DFRobot SEN0308 capacitive | ADC GPIO 2 |
| Environmental | BME280 (temp/humidity/pressure) | I2C SDA=4 SCL=5 |
| Light/lux | DFRobot SEN0390 / VEML7700 | I2C SDA=4 SCL=5 |
| Leaf wetness | Optional RS485/Modbus sensor | UART2 |
| Battery | 12 V Li-Ion 3S pack via ADC divider | ADC GPIO 1 |
| Sensor power | GPIO 38 → MOSFET rail | GPIO |

See `docs/NODE_WIRING.md` for the full pin table and wiring diagrams.

---

## Build Environments

| Environment | Description |
|-------------|-------------|
| `debug_serial` | Mock sensors, print JSON to Serial — **no radio required** |
| `lora_p2p` | LoRa P2P compact JSON → local gateway, real sensors, deep sleep |
| `lorawan_otaa` | LoRaWAN OTAA via RadioLib + US915, real sensors, deep sleep |
| `lora_p2p_precision` | Same as `lora_p2p` + leaf wetness + solar ADC |
| `debug_serial_esp32dev` | Generic ESP32 devkit, mock sensors |
| `native_test` | Host-side unit tests (no MCU needed) |

---

## Quick Start

### 1. Install PlatformIO

```bash
pip install platformio
# or install the VS Code extension
```

### 2. Debug without hardware (mock sensors)

```bash
cd firmware/esp32-node
pio run --environment debug_serial
pio run --environment debug_serial --target upload
pio device monitor --baud 115200
```

You should see `VGPAYLOAD:{...}` lines with realistic mock vineyard data.

### 3. Provision a real node (LoRa P2P mode)

```bash
# Copy example manifest and fill in real LoRaWAN/device keys
cp tools/provisioning_manifest.example.csv tools/provisioning_manifest.csv
# Edit provisioning_manifest.csv

# Generate keys header and flash
./tools/flash_device.sh --serial VG-000001 --env lora_p2p
# Windows:
# .\tools\flash_device.ps1 -Serial VG-000001 -Env lora_p2p
```

See `docs/PROVISIONING.md` for the full flow.

### 4. LoRaWAN OTAA mode

```bash
# First provision lorawan_keys.h
python tools/make_keys_header.py --serial VG-000001

# Build and flash
./tools/flash_device.sh --serial VG-000001 --env lorawan_otaa
```

### 5. Run unit tests (no MCU needed)

```bash
pio test --environment native_test
```

---

## Serial Output Format

In `debug_serial` or `lora_p2p` mode the node emits:

```
VGPAYLOAD:{"schema_version":"1.0","device_id":"vg-node-001","tier":"basic","sensors":{...},"meta":{...}}
```

The gateway reads these lines in `LORA_MODE=serial_json` mode.

---

## Key Files

```
include/
  build_config.h         Build-time feature flags
  pins.h                 Pin definitions per board
  config.h               Device defaults and calibration
  payload_schema.h       Binary frame layout constants
  lorawan_keys.example.h LoRaWAN key template (copy → lorawan_keys.h)
  calibration.example.h  Calibration value template

src/
  main.cpp               Minimal setup/loop → AppController
  app/AppController.*    Orchestrates sample-transmit cycle
  app/TelemetryBuilder.* Builds V1 JSON and compact LoRa JSON payloads
  app/SleepManager.*     Deep sleep with RTC memory
  sensors/               One driver per sensor type
  comms/                 UplinkClient interface, SerialDebug, LoRaP2P, LoRaWAN
  storage/               FailsafeQueue (SPIFFS), NvsConfigStore (NVS)
  util/                  Logger, CRC16, TimeUtil

tools/
  make_keys_header.py    Generate lorawan_keys.h from provisioning CSV
  flash_device.sh/.ps1   One-command provision + build + flash
  decode_payload.py      Decode compact JSON or binary payloads
  serial_smoke_test.py   Verify a freshly-flashed node over USB serial
  provisioning_manifest.example.csv  Example per-node manifest
```

---

## Configuration

### Build-time (platformio.ini `build_flags`)

| Flag | Default | Description |
|------|---------|-------------|
| `BOARD_HELTEC_V3` | — | Target Heltec WiFi LoRa 32 V3 |
| `BUILD_MODE_DEBUG_SERIAL` | set in debug_serial | Print JSON to serial |
| `BUILD_MODE_LORA_P2P` | set in lora_p2p | LoRa P2P uplink |
| `BUILD_MODE_LORAWAN_OTAA` | set in lorawan_otaa | LoRaWAN OTAA |
| `MOCK_SENSORS` | set in debug_serial | Simulate sensor readings |
| `ENABLE_LEAF_WETNESS` | 0 | Enable RS485 leaf wetness sensor |
| `ENABLE_SOLAR_ADC` | 0 | Enable solar voltage ADC |
| `USE_DEEP_SLEEP` | 0 debug / 1 lora | Enable deep sleep between cycles |
| `SAMPLE_INTERVAL_S` | 15 debug / 900 lora | Seconds between samples |
| `TRANSMIT_INTERVAL_S` | 15 debug / 900 lora | Seconds between uplinks |
| `DEBUG_LEVEL` | 2 debug / 1 lora | 0=silent 1=info 2=verbose |

### Runtime (NVS, via provisioning)

Stored by `NvsConfigStore`:
- `device_id`, `node_serial`, `vineyard_id`, `block_id`, `node_type`
- `sample_s`, `transmit_s`
- Calibration: `soil_dry_adc`, `soil_wet_adc`, `batt_divider`

---

## Smoke Test After Flash

```bash
python tools/serial_smoke_test.py --port /dev/ttyUSB0
# Windows:
# python tools\serial_smoke_test.py --port COM3
```

Checks boot, payload emission, JSON validity, and sensor ranges.

---

## Known Limitations

1. **LoRaWAN API** — RadioLib LoRaWAN is tested against 6.4.x. The API has changed across versions; if compile errors occur, check the RadioLib changelog and adjust the `TODO: RadioLib 6.x` comments in `LoRaWanClient.cpp`.

2. **Leaf wetness Modbus map** — The `LeafWetnessSensor` contains a placeholder Modbus implementation. The register map must be filled in once the sensor datasheet is confirmed (see TODO comments in `LeafWetnessSensor.cpp`).

3. **RTC timestamp** — The node does not have a real-time clock. The gateway assigns the wall-clock timestamp on receipt. For LoRaWAN, the network server provides the timestamp.

4. **ADC accuracy** — ESP32 ADC has ±5% non-linearity at full scale. For best accuracy enable ADC calibration using `esp_adc_cal_characterize()` (a future enhancement).

5. **LoRa P2P no ACK** — The current P2P implementation is send-only; the gateway does not send downlink ACKs. Add a brief receive window if acknowledgment is needed.

6. **OTA** — OTA is stubbed; only applicable when Wi-Fi is available during a maintenance window. See `docs/OTA_STRATEGY.md`.
