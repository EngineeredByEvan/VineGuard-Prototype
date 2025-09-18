# VineGuard ESP32 Node Firmware

Prototype firmware for the VineGuard in-field sensing node. The firmware targets ESP32 boards using the Arduino framework and PlatformIO. It samples soil and environmental sensors, publishes telemetry via LoRaWAN-style LoRa uplink or Wi-Fi/MQTT (lab mode), and persists runtime configuration in NVS.

## Features

- Modular sensor layer with swappable drivers (`AnalogSoilMoistureSensor`, `SoilTemperatureSensor`, `AmbientClimateSensor`, `LightSensor`, `BatteryMonitor`). Mock readings are emitted in `LAB_MODE` so the application can run on a desk without physical sensors.
- FreeRTOS task architecture:
  - `sensingTask` performs sensor acquisition when triggered.
  - `uplinkTask` builds JSON telemetry and handles LoRa/MQTT transport.
  - `powerTask` orchestrates sampling cadence, deep sleep, OTA triggers, and configuration reloads.
- Configuration structure (`NodeConfig`) stored in NVS with defaults. Includes publish interval, sleep strategy, org/site/node identifiers, and MQTT credentials.
- Transport abstraction with LoRa (Semtech SX1276/8) or Wi-Fi → MQTT (lab mode) via `ITelemetryPublisher` implementations.
- MQTT command handling for `set_config` and OTA URL updates. OTA uses HTTPS (`ESPhttpUpdate`).
- Status LED patterns for OK (slow blink), error (double blink), and OTA (fast blink) states.
- Helper library (`SensorMath`, `TelemetryBuilder`) with unit tests executed on the `native` PlatformIO environment.

## Project Layout

```
firmware/esp32-node/
├── config.h.example        # Copy to config.h to override lab credentials or pin mappings
├── include/                # Public headers for sensors, config, comms, LED, etc.
├── lib/node_common/        # Pure helper modules with unit tests
├── src/                    # Application sources and FreeRTOS tasks
├── test/                   # Native unit tests for helper functions
└── platformio.ini          # PlatformIO configuration (ESP32 + native test env)
```

## Building

Install PlatformIO (CLI) and run:

```bash
pio run -d firmware/esp32-node          # build default LoRa-focused firmware
pio run -e esp32dev_lab_wifi -d firmware/esp32-node   # build with LAB_MODE + Wi-Fi MQTT stub
```

Run helper unit tests on the host:

```bash
pio test -e native -d firmware/esp32-node
```

## Configuration

Runtime configuration is persisted in NVS. Default values are compiled from `config_defaults.h`. To supply lab credentials (Wi-Fi SSID/password, MQTT broker, LoRa pin mapping), copy `config.h.example` to `config.h` and edit as needed.

Example configuration command via MQTT (topic `/<org>/<site>/<node>/cmd`):

```json
{
  "cmd": "set_config",
  "config": {
    "publishIntervalSeconds": 300,
    "sleepStrategy": "stayAwake",
    "useLoRa": false,
    "mqtt": {
      "host": "lab-broker.local",
      "port": 1883,
      "username": "lab",
      "password": "lab"
    },
    "identity": {
      "org": "vineguard",
      "site": "lab",
      "node": "esp32-node"
    }
  }
}
```

To request an OTA update:

```json
{
  "cmd": "ota",
  "otaUrl": "https://example.com/firmware.bin"
}
```

`set_config` payloads that contain `otaUrl` will also trigger the OTA process.

## Telemetry Payload

Telemetry is published as JSON matching the MQTT contract. Example:

```json
{
  "version": "0.1.0",
  "org": "vineguard",
  "site": "lab",
  "node": "esp32-node",
  "ts": 1697049600000,
  "measurements": {
    "soilMoisture": 0.42,
    "soilTempC": 19.5,
    "ambientTempC": 21.1,
    "ambientHumidity": 56.0,
    "lightLux": 123.4,
    "batteryVoltage": 3.71
  }
}
```

## LAB_MODE

`LAB_MODE` (and `LAB_MODE_WIFI`) can be enabled via the `esp32dev_lab_wifi` PlatformIO environment. In this mode:

- Sensors emit deterministic mock values for bench testing.
- MQTT publishing is stubbed; telemetry is printed to the serial console and command messages can be injected by sending JSON lines over the serial port.
- Deep sleep is disabled so tasks continue to run on the desk.

Monitor serial output at 115200 baud to view telemetry samples and command responses.
