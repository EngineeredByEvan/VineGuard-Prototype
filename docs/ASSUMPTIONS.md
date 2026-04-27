# VineGuard MVP Implementation Assumptions

This document records every design decision made without confirmed hardware measurements, field data, or third-party protocol documentation. Each assumption should be validated during the first bench test and field installation.

---

## Hardware

**1. Target board is Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)**
- Assumed pin assignments are taken from the Heltec V3 schematic (rev 3.1).
- If using Heltec V2 (ESP32 non-S3), the SX1262 SPI pins differ; update `include/pins.h`.
- If using TTGO LoRa32, M5Stack LoRa, or a custom board, define `BOARD_CUSTOM` and provide `pins_custom.h`.

**2. SX1262 uses TCXO reference**
- The Heltec V3 schematic shows a 26 MHz TCXO. `LoRaRadioClient::initRadio()` calls `_radio.setTCXO(1.8f)`. This is non-fatal if the board does not have a TCXO (RadioLib logs a debug warning and continues).

**3. RadioLib 6.4.x API**
- LoRaWAN and SX1262 APIs tested against RadioLib 6.4.x. The LoRaWAN API changed significantly between 5.x, 6.x, and 7.x. The `TODO: RadioLib 6.x` comments in `LoRaWanClient.cpp` mark the exact lines that may need adjustment.

---

## Power System

**4. 12V Li-Ion 3S pack**
- `BATTERY_VOLTAGE_MAX = 12.6 V`, `BATTERY_VOLTAGE_MIN = 9.0 V`.
- If using a 4S pack (14.4 V max) or a single-cell LiPo (4.2 V max), update both thresholds in `config.h` and adjust the ADC divider ratio.

**5. External voltage divider required for 12V**
- The Heltec V3 onboard 100k/100k divider (GPIO 1) only handles ≤ ~8.4 V safely. The VineGuard 12 V pack requires an external 100k/11k divider. The firmware defaults to `BATTERY_DIVIDER_RATIO = 2.0` (onboard). **Update this to 10.09** in `calibration.local.h` before deploying 12 V pack nodes.

**6. Solar charging produces 12–14.4 V**
- Assumed based on a 10 A PWM charge controller with a 12V nominal setting. MPPT controllers may float at a different voltage. ENABLE_SOLAR_ADC=1 uses the same 100k/11k divider approach on GPIO 3.

---

## Sensors

**7. SEN0308 output polarity is inverse (dry = high ADC)**
- DFRobot SEN0308 uses a 555-timer-based capacitive circuit that outputs a higher voltage in dry conditions and lower voltage in wet conditions.
- `SoilMoistureSensor::adcToPercent()` implements `pct = (dry - raw) / (dry - wet) * 100`.
- If your soil moisture sensor has the opposite polarity (common for resistive sensors), invert the formula.

**8. SEN0308 calibration values are installation-specific**
- Default `SOIL_DRY_ADC_VALUE = 2800`, `SOIL_WET_ADC_VALUE = 800` are approximate for a 12-bit ESP32 ADC with `ADC_11db` attenuation.
- **Calibrate every installed probe** using the procedure in `include/calibration.example.h`.

**9. BME280 I2C address is 0x76**
- `BME280_I2C_ADDR = 0x76` (SDO pin pulled LOW). If your breakout board has SDO pulled HIGH, change to `0x77` in `config.h`.

**10. DFRobot SEN0390 uses VEML7700**
- Confirmed by the DFRobot product wiki (DFR0095/SEN0390). The Adafruit VEML7700 library is used directly.
- If a different lux sensor is substituted (e.g. BH1750 at 0x23), replace `LuxSensor.cpp` with the appropriate driver.

**11. Leaf wetness sensor uses Modbus RTU at 9600 baud**
- The exact sensor model and register map are **unconfirmed**. `LeafWetnessSensor.cpp` contains a placeholder Modbus implementation.
- **Required before precision+ nodes can be certified**: confirm the physical sensor's Modbus slave address, baud rate, register address, and raw value scaling from the datasheet. Update the `TODO` sections in `LeafWetnessSensor.cpp`.
- Assumed: single holding register at address 0x0000, 12-bit raw value (0–4095). Set `SENSOR_OUTPUTS_PERCENT = true` if the sensor outputs 0–100 directly.

---

## Radio and LoRa

**12. LoRa P2P channel: 915.0 MHz, SF9, BW 125 kHz, CR 4/7**
- This is a reasonable default for a vineyard with 50–500 m gateway distance.
- Gateway must be configured to the same frequency, SF, BW, and sync word (0x12 private).
- For longer range (> 1 km), increase SF to 10 or 11 (trades airtime for range).
- For shorter range with higher data rate, reduce to SF7.
- Defined in `include/build_config.h` as `LORA_*` constants.

**13. LoRaWAN sub-band 2 (channels 8–15 + 65)**
- US915 has 8 configurable sub-bands. Sub-band 2 is used by TTN, Helium, and AWS IoT Core for LoRaWAN in the US/Canada.
- If your network server uses a different sub-band, change `LORAWAN_SUBBAND` in `build_config.h`.

**14. LoRa P2P payloads are < 222 bytes**
- Compact JSON payloads are ~120–150 bytes at SF7 max payload. The firmware logs a warning and truncates if the payload exceeds 220 bytes.
- V1 JSON payloads (~300 bytes) are NOT sent over LoRa P2P; only compact JSON is used for P2P uplinks.

---

## Gateway

**15. Gateway runs on a Raspberry Pi or Linux mini-PC within LoRa range**
- Assumed to be within the vineyard building or field shed, < 500 m from the furthest node.
- For larger deployments, a rooftop-mounted Raspberry Pi with an outdoor LoRa concentrator antenna is assumed.

**16. MQTT broker is the same broker used by the existing cloud stack**
- `MQTT_TOPIC = vineguard/telemetry` matches the existing ingestor subscription.
- The gateway uses QoS 1 (at-least-once). The ingestor is idempotent by design (duplicate messages result in duplicate DB rows, not data corruption — an acceptable trade-off for MVP).

---

## Cloud

**17. No database migration required for MVP sensor set**
- The `telemetry_readings` table already has columns for all MVP sensors: `soil_moisture`, `ambient_temp_c`, `ambient_humidity`, `light_lux`, `battery_voltage`, `leaf_wetness_pct` (nullable), `pressure_hpa` (nullable).
- The ingestor's `TelemetryPayloadV1` schema already validates all these fields.
- **No cloud changes are required** to support the new firmware.

**18. Analytics rules use server-side recorded_at for time windows**
- All analytics rules (moisture, frost, mildew MPI, GDD, canopy lux) query `recorded_at` from the database, not the node's reported timestamp.
- This is correct behaviour: the node timestamp is unreliable (no RTC), but the server timestamp is authoritative.

---

## Timing

**19. 15-minute sample interval satisfies analytics resolution**
- Mildew MPI rule calculates "wet hours" as `count(leaf_wetness_pct > 0) × 0.5` (assuming 30-min intervals).
- At 15-min sampling, the wet hour calculation uses `× 0.25` instead. The analytics rule in `mildew_mpi.py` may need updating for 15-min data if precision is required.
- For MVP, the approximation is acceptable.

**20. Sensor warm-up of 500 ms is sufficient**
- BME280 datasheet specifies < 2 ms for a forced measurement to complete after command. The 500 ms accounts for:
  - MOSFET switching time
  - Power rail capacitor charging
  - I2C bus stabilisation
  - BME280 factory calibration load time on cold boot
- In temperatures below 0°C, consider increasing to 1000 ms.
