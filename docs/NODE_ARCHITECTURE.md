# VineGuard Node Firmware Architecture

## Overview

The node firmware is a modular C++/Arduino application built with PlatformIO, targeting the Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262). The design prioritises:

- **Reliability** — every sensor failure is tolerated; the node keeps transmitting with partial data.
- **Low power** — sensors are switched off between samples; deep sleep keeps average current < 1 mA.
- **Maintainability** — one class per concern, minimal abstractions, clear TODOs where hardware specifics are unknown.

---

## Module Map

| Directory | Key Files | Purpose |
|-----------|-----------|---------|
| `include/` | `build_config.h`, `pins.h`, `config.h` | Compile-time constants, pin assignments, calibration defaults |
| `src/app/` | `AppController`, `TelemetryBuilder`, `SleepManager` | Application orchestration, payload construction, sleep management |
| `src/sensors/` | `SensorManager`, `*Sensor` drivers | Power rail control, sensor init/read, validity flags |
| `src/comms/` | `UplinkClient`, `SerialDebugUplink`, `LoRaRadioClient`, `LoRaWanClient` | Uplink transport abstraction and implementations |
| `src/storage/` | `FailsafeQueue`, `NvsConfigStore` | SPIFFS payload queue and NVS config persistence |
| `src/ota/` | `OtaUpdater` | Stub OTA check (disabled for LoRa-only MVP) |
| `src/util/` | `Logger`, `Crc`, `TimeUtil` | Logging macros, CRC-16, dew point, battery percent |

---

## Boot and Task Flow

```
Power-on / Wake from deep sleep
         │
         ▼
  Logger::init()          ← Serial at 115200 baud
  NvsConfigStore::load()  ← Read device_id, intervals, node_type from NVS
  NvsConfigStore::incrementBootCount()
  FailsafeQueue::begin()  ← Mount SPIFFS, recount cached payloads
         │
         ▼
  SensorManager::begin()
    ├─ Wire.begin(SDA=4, SCL=5)
    ├─ GPIO 38 HIGH (power rail on)
    ├─ delay(SENSOR_WARMUP_MS=500)
    ├─ SoilMoistureSensor::init()
    ├─ Bme280Sensor::init()
    ├─ LuxSensor::init()
    ├─ [LeafWetnessSensor::init()]  ← only if ENABLE_LEAF_WETNESS=1
    └─ GPIO 38 LOW (power rail off)
         │
         ▼
  UplinkClient::begin()
    ├─ DEBUG_SERIAL  → SerialDebugUplink (always ready)
    ├─ LORA_P2P      → LoRaRadioClient::initRadio() via SPI
    └─ LORAWAN_OTAA  → LoRaWanClient::initRadio() + joinOTAA()
         │
  ┌──────▼──────────────────────────────────────────┐
  │              AppController::loop()               │
  │                                                  │
  │  1. SleepManager::getAndIncrementSequence()      │
  │  2. SensorManager::sample()                      │
  │       GPIO 38 HIGH → read all sensors → LOW      │
  │  3. BatteryMonitor::read() (after rail off)      │
  │  4. TelemetryBuilder::buildV1Json()              │
  │     TelemetryBuilder::buildCompactJson()         │
  │  5. FailsafeQueue::drain() (up to 5 cached)      │
  │  6. UplinkClient::send()                         │
  │       success → continue                         │
  │       failure → FailsafeQueue::push()            │
  │  7. [OtaUpdater::checkAndApply() — no-op MVP]    │
  │  8. Determine sleep duration                     │
  │       normal     → cfg.sampleIntervalS           │
  │       low batt   → × 2                           │
  │       critical   → × 4, skip transmit            │
  │  9. SleepManager::deepSleep(durationSec)         │
  └──────────────────────────────────────────────────┘
         │
  USE_DEEP_SLEEP=1 → esp_deep_sleep_start() [never returns]
  USE_DEEP_SLEEP=0 → blocking delay, loop repeats
```

---

## Sensor Lifecycle

```
Cycle start
   │
   ▼ GPIO 38 HIGH  ← N-channel MOSFET enables sensor VCC rail
   │ delay 500 ms  ← BME280 needs ~2 ms; 500 ms ensures stable ADC refs too
   │
   ├─ analogRead(SOIL_MOISTURE_PIN)  → raw ADC → voltage → percent
   ├─ Adafruit_BME280::takeForcedMeasurement() → T / RH / P
   ├─ Adafruit_VEML7700::readLux(VEML_LUX_AUTO)
   └─ [RS485 Modbus read — ENABLE_LEAF_WETNESS=1]
   │
   ▼ GPIO 38 LOW   ← Cut sensor power before sleep / battery read
   │
   └─ analogRead(BATTERY_ADC_PIN) × 4  → average → × divider → voltage → %
```

Each sensor driver sets a validity flag (`soilOk`, `bme280Ok`, etc.). If a sensor fails to initialise or returns an out-of-range value, the flag is `false` and the field is set to a sentinel value (–1 or –999). The payload serialiser emits `null` for invalid readings. The cloud ingestor accepts nulls for all optional sensor fields.

---

## Power / Deep Sleep Lifecycle

| Variable | Storage | Initial value | Role |
|----------|---------|---------------|------|
| `rtcSequence` | `RTC_DATA_ATTR` | 0 (reset on power-off) | Monotonic uplink counter |
| `rtcUptimeSec` | `RTC_DATA_ATTR` | 0 | Cumulative awake+sleep time |
| `boot_count` | NVS Preferences | 0 | Total power-on + wake count |

`RTC_DATA_ATTR` variables survive deep sleep but reset on power-off. NVS survives power cycles.

Deep sleep sequence (USE_DEEP_SLEEP=1):
1. `rtcUptimeSec += sleepDurationSec`
2. `esp_sleep_enable_timer_wakeup(sleepDurationSec * 1e6)`
3. `esp_deep_sleep_start()` — MCU halts, only RTC domain powered
4. After timer: full reset, execution restarts from `setup()`

Debug mode (USE_DEEP_SLEEP=0): `SleepManager::debugDelay()` replaces deep sleep with a blocking `delay()` loop. The serial monitor stays open.

---

## Communication Modes

### DEBUG_SERIAL_ONLY
- `SerialDebugUplink` writes `VGPAYLOAD:<json>\r\n` to USB serial.
- No radio initialised.
- Gateway can read these lines in `LORA_MODE=serial_json`.

### LORA_P2P
- `LoRaRadioClient` initialises SX1262 via RadioLib.
- Transmits compact JSON payload (~130 bytes) at 915 MHz SF9 BW125.
- No join procedure; gateway listens on matching frequency/SF/BW.
- Compact JSON key map is documented in `PAYLOAD_CONTRACT.md`.

### LORAWAN_OTAA
- `LoRaWanClient` uses RadioLib `LoRaWANNode` with US915 region, sub-band 2.
- OTAA join on first boot; session keys persisted in RTC memory.
- Uplinks encoded as VGPP-1 binary (~22 bytes) on FPort 1.
- If join fails `LORAWAN_MAX_REJOIN_ATTEMPTS` times, session is cleared and a fresh join is attempted next cycle.

---

## Failsafe Queue

- Backed by SPIFFS (`/vg_queue.jsonl`).
- Max depth: `FAILSAFE_QUEUE_MAX_DEPTH = 48` entries ≈ 12 hours at 15-min intervals.
- On transmit failure: current payload is pushed to tail of queue.
- On next successful cycle: up to 5 queued payloads are drained before the fresh payload is sent.
- If queue is full, the oldest entry is dropped to make room (FIFO eviction).
- Queue depth is reported in every telemetry payload (`queue_depth` field).

---

## Known Limitations

1. **No real-time clock** — the node has no GPS or NTP. The `timestamp` field in the payload contains seconds since last power-on. The gateway replaces it with the wall-clock UNIX epoch on receipt.
2. **RadioLib version sensitivity** — LoRaWAN API changed between RadioLib 5.x, 6.x, and 7.x. The LoRaWanClient targets 6.4.x. Check the TODO comments in `LoRaWanClient.cpp` if compilation fails.
3. **ADC non-linearity** — ESP32 ADC has ±5% non-linearity near the ends of its range. For best accuracy add `esp_adc_cal_characterize()` calibration (a future enhancement, not required for MVP).
4. **No LoRa downlink ACK** — LoRa P2P mode is unidirectional. The gateway does not send ACKs. If confirmed delivery is required, switch to LoRaWAN which has MAC-layer ACKs.
5. **Leaf wetness Modbus map** — the RS485 driver uses a placeholder register map that must be confirmed against the physical sensor datasheet (see TODO in `LeafWetnessSensor.cpp`).
