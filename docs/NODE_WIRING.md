# VineGuard Node Wiring Guide

## Target Board

**Heltec WiFi LoRa 32 V3** — ESP32-S3 + SX1262 (915 MHz), USB-C, 0.96" OLED (disabled by default).

> If using a generic ESP32 devkit for bench testing, define `BOARD_GENERIC_ESP32` in `platformio.ini` and use the `debug_serial_esp32dev` environment. The generic pin assignments are in `include/pins.h`.

---

## Complete Pin Table

| GPIO | Label | Connected To | Notes |
|------|-------|-------------|-------|
| 1 | VBAT_ADC | Battery ADC divider midpoint | Onboard 100k/100k divider on Heltec V3; see §Battery Divider |
| 2 | SOIL_MOISTURE | DFRobot SEN0308 signal wire | 12-bit ADC, ADC_11db (0–3.3 V) |
| 3 | SOLAR_ADC | Solar charger voltage divider | Only if ENABLE_SOLAR_ADC=1 |
| 4 | EXT_I2C_SDA | BME280 SDA + VEML7700 SDA | External I2C bus (separate from OLED) |
| 5 | EXT_I2C_SCL | BME280 SCL + VEML7700 SCL | " |
| 6 | RS485_TX | MAX485 DI (data in) | UART2 TX; ENABLE_LEAF_WETNESS=1 only |
| 7 | RS485_RX | MAX485 RO (receiver out) | UART2 RX |
| 8 | LORA_NSS | SX1262 CS | Onboard, do not use externally |
| 9 | LORA_SCK | SX1262 SCK | Onboard |
| 10 | LORA_MOSI | SX1262 MOSI | Onboard |
| 11 | LORA_MISO | SX1262 MISO | Onboard |
| 12 | LORA_RST | SX1262 RST | Onboard |
| 13 | LORA_BUSY | SX1262 BUSY | Onboard |
| 14 | LORA_DIO1 | SX1262 DIO1 / IRQ | Onboard |
| 17 | OLED_SDA | OLED SSD1306 SDA | Onboard; OLED disabled (ENABLE_OLED=0) |
| 18 | OLED_SCL | OLED SSD1306 SCL | Onboard |
| 21 | OLED_RST | OLED reset | Onboard |
| 35 | LED | Onboard LED (active HIGH) | Status blink on transmit |
| 38 | SENSOR_POWER | MOSFET gate (sensor power rail) | HIGH = sensors powered |
| 47 | RS485_DE | MAX485 DE+RE tied together | HIGH = transmit mode |
| 0 | BUTTON | User boot button (active LOW) | Also boot strap, do not pull HIGH |

---

## I2C Bus (BME280 + VEML7700 Lux)

Both sensors share the **external** I2C bus on GPIO 4 (SDA) and GPIO 5 (SCL).

```
3.3V ──┬──[4.7kΩ]──┬── SDA (GPIO 4)
       │            ├── BME280 SDA
       │            └── VEML7700 SDA
       │
3.3V ──┴──[4.7kΩ]──┬── SCL (GPIO 5)
                    ├── BME280 SCL
                    └── VEML7700 SCL

BME280  address: 0x76 (SDO → GND) or 0x77 (SDO → 3.3V)
VEML7700 address: 0x10 (fixed)
```

**Pull-up values:**
- Cable ≤ 0.5 m: 4.7 kΩ
- Cable 0.5–1 m: 4.7 kΩ (OK)
- Cable 1–2 m: 2.2 kΩ (reduce to keep rise time < 1 µs at 100 kHz)

**BME280 wiring (radiation shield pod):**
- Use 4-core cable (VCC, GND, SDA, SCL) with drain wire
- Cable runs from main enclosure to radiation shield 15–30 cm away
- Terminate cable at both ends inside enclosures; secure with cable glands
- Do NOT expose BME280 to direct sunlight (use a proper radiation shield)

**VEML7700 (lux sensor) wiring:**
- Same 4-core cable, length up to 2 m
- Sensor mounted under canopy or at vine height
- Point sensor element upward into canopy
- Use 2.2 kΩ pull-ups if cable > 1 m

---

## Soil Moisture Sensor (DFRobot SEN0308)

```
Sensor rail (GPIO 38 MOSFET output)
    │
   VCC ── SEN0308
   GND ── GND
   SIG ──────── GPIO 2 (ADC)
```

- The SEN0308 outputs an **inverse** analog voltage: **dry soil → higher voltage**, **wet soil → lower voltage**.
- The firmware maps ADC counts using `SOIL_DRY_ADC_VALUE` (high count in air) and `SOIL_WET_ADC_VALUE` (low count in water). Run the `debug_serial` build to observe raw ADC values during calibration.
- ADC is configured for 12-bit resolution (0–4095) with `ADC_11db` attenuation (0–3.3 V input range).
- Insert the probe tip at 4–6 inch depth in the root zone. Avoid placing it in rocks or highly compacted soil.
- Waterproof the connector joint between sensor cable and node cable with self-amalgamating tape and/or a heat-shrink boot.

---

## Battery ADC Voltage Divider

### Heltec V3 onboard divider (single-cell LiPo only)

The Heltec V3 has a 100 kΩ / 100 kΩ resistor divider on GPIO 1, suitable for a 3.7 V single-cell LiPo (max 4.2 V × 2 = 8.4 V at the ADC pin — within the 3.3 V ADC range). **This divider is NOT suitable for the 12 V Li-Ion pack.**

### External divider for 12 V Li-Ion pack

For the VineGuard 3S Li-Ion pack (9.0–12.6 V) use an external resistor divider:

```
12V PACK (+) ─── [100 kΩ] ─── ADC_PIN ─── [11 kΩ] ─── GND
                               │
                              [100 nF] bypass capacitor to GND
```

- Divider ratio: (100k + 11k) / 11k ≈ **10.09**
- At full charge (12.6 V): ADC_PIN ≈ 1.25 V → ADC count ≈ 1548
- At cutoff (9.0 V): ADC_PIN ≈ 0.89 V → ADC count ≈ 1104

Update `BATTERY_DIVIDER_RATIO 10.09` in `config.h` (or `calibration.local.h`) and set the GPIO to a free pin. **Do not use GPIO 1** if the onboard divider is wired to a LiPo.

> **Safety:** add a 500 mA polyfuse between the battery positive terminal and the divider to protect against wiring errors.

---

## Solar Voltage ADC (Optional, ENABLE_SOLAR_ADC=1)

Same approach as battery divider. Use GPIO 3:

```
SOLAR_VOUT (+) ─── [100 kΩ] ─── GPIO 3 ─── [11 kΩ] ─── GND
                                 │
                                [100 nF] to GND
```

Typical solar charger output: 13–14.4 V on a sunny day, 0 V at night. Use the same ratio 10.09.

---

## Sensor Power Rail (MOSFET Switch)

GPIO 38 controls an N-channel MOSFET that switches the 3.3 V sensor VCC rail on and off.

```
3.3V ──────────────────────────────── SENSOR_VCC (to BME280, VEML7700, SEN0308 VCC)
                │
            [MOSFET drain]
           N-channel (e.g. AO3400 / 2N7002)
            [MOSFET source] ── GND
            [MOSFET gate]  ── [10 kΩ pull-down to GND] ── GPIO 38

GPIO 38 HIGH → MOSFET on  → sensors powered
GPIO 38 LOW  → MOSFET off → sensors unpowered (saves ~3–8 mA)
```

**Part options:**
- AO3400 (SOT-23, Vgs(th) ≈ 0.9 V, Id = 5.7 A) — preferred
- 2N7002 (SOT-23, logic-level, Id = 300 mA) — adequate for 3 small sensors
- BSS138 (SOT-23, Vgs(th) ≈ 1.5 V at 3.3 V drive) — marginal, avoid

---

## RS485 / MAX485 Wiring (Leaf Wetness, ENABLE_LEAF_WETNESS=1)

```
MAX485 module
  VCC ──── 3.3V (from sensor rail)
  GND ──── GND
  DI  ──── GPIO 6  (UART2 TX)
  RO  ──── GPIO 7  (UART2 RX)
  DE  ─┬─ GPIO 47  (HIGH = transmit)
  RE  ─┘

  A ─────── RS485 A line ─────── Leaf wetness sensor A
  B ─────── RS485 B line ─────── Leaf wetness sensor B
                │
            [120 Ω termination resistor across A–B at far end if cable > 1 m]
```

- Half-duplex: GPIO 47 HIGH before writing, LOW before reading.
- Default baud: 9600 (`RS485_BAUD_RATE` in config.h).
- Cable type: twisted pair (CAT5e, Belden 9841) preferred.
- Max reliable cable length: 100 m at 9600 baud.

---

## Power Supply Schematic

```
Solar Panel (20W, Voc ≈ 21V)
        │
  [Solar Charge Controller]  ← e.g. Renogy Wanderer 10A
        │
  12V Li-Ion Pack (3S, 3–10 Ah)
        │
      [Fuse 3A]
        │
  [Buck Converter 12V → 5V, 2A]  ← e.g. LM2596 module
        │
  Heltec V3 5V pin (or USB-C if ≤ 500 mA)
        │
  Heltec 3.3V LDO output → Sensor rail MOSFET drain
```

> The Heltec V3 5V input tolerance is typically 4.5–6V. Do not connect 12V directly.

---

## Enclosure and Waterproofing

- **Enclosure**: IP65+ rated junction box (e.g. Hammond 1554, Polycase WC-17).
- **Cable glands**: PG7 for sensor cables (4–7 mm OD), PG9 for power cable.
- **Gland placement**: face all glands **downward** to prevent water tracking into the gland.
- **BME280 radiation shield**: 3D-print a Stevenson screen or use a Gill Instruments MaxiMet aspirated shield. Mount 15–30 cm from the main enclosure on a short arm.
- **Lux sensor**: IP67-rated VEML7700 breakout with conformal coating, or pot the sensor in epoxy leaving only the sensor window exposed.
- **Soil probe**: the SEN0308 probe body is waterproof; seal the cable entry point with self-amalgamating tape.

---

## Approximate BOM

| Item | Quantity |
|------|----------|
| Heltec WiFi LoRa 32 V3 | 1 |
| DFRobot SEN0308 soil moisture sensor | 1 |
| BME280 breakout module | 1 |
| DFRobot SEN0390 / VEML7700 lux sensor | 1 |
| Optional: RS485 leaf wetness sensor | 1 |
| MAX485 TTL-to-RS485 module | 1 (precision+ only) |
| AO3400 N-channel MOSFET (SOT-23) | 1 |
| Resistors: 4.7 kΩ × 2, 10 kΩ × 1, 100 kΩ × 1, 11 kΩ × 1, 120 Ω × 1 | assorted |
| Capacitors: 100 nF × 2 | assorted |
| IP65+ enclosure ~100×68×50 mm | 1 |
| PG7 cable glands | 4–6 |
| 4-core shielded cable (BME280, lux) 1–2 m | 2 lengths |
| 2-core or 3-core cable (soil, RS485) | 1–2 lengths |
| 12V Li-Ion 3S pack 3–5 Ah | 1 |
| 20W solar panel | 1 |
| 10A solar charge controller | 1 |
| 12V → 5V buck converter module | 1 |
| DIN-rail or panel-mount fuse holder, 3A fuse | 1 |
