# VineGuard™ ESP32 Node Firmware

This PlatformIO project targets solar-powered ESP32 telemetry nodes. The
firmware is organised around FreeRTOS tasks for telemetry and OTA update checks
and is structured for low-power operation and modular sensor drivers.

## Features

- Periodic soil/ambient sensor sampling (stubbed with random data for now)
- JSON payload preparation for LoRa uplink
- OTA update hook for secure binary delivery
- Power-saving deep sleep configuration between measurement intervals
- Configurable identifiers and credentials via `DeviceConfig`

## Getting Started

1. Install [PlatformIO](https://platformio.org/).
2. Copy `platformio.ini` to your local workspace and adjust board type if
   necessary.
3. Provide real sensor driver implementations in `readSensors()` and integrate
   the chosen LoRaWAN stack in `connectLoRa()`/`publishReadings()`.
4. Configure secure OTA endpoint and TLS validation in `checkForOtaUpdates()`.
5. Build and upload: `pio run --target upload`.

## Power & OTA Notes

- Update the sleep interval to balance energy use with telemetry frequency.
- Use signed OTA binaries and validate certificates before flashing.
- Ensure the LoRa keys and MQTT credentials are injected securely at build time
  or retrieved from encrypted storage.
