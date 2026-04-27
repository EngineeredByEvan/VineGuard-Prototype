#pragma once
// pins.h — hardware pin assignments per board variant
//
// Select your board by defining BOARD_HELTEC_V3 or BOARD_GENERIC_ESP32
// in platformio.ini build_flags.  To use a custom layout define
// BOARD_CUSTOM and fill in all PIN_* constants below it.
//
// Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262, 915 MHz)
// Schematic: https://resource.heltec.cn/download/WiFi_LoRa_32_V3/HTIT-WB32LA(F)_V3.1.pdf

#if defined(BOARD_HELTEC_V3)

  // SX1262 SPI bus (dedicated, not shared with peripherals)
  #define PIN_LORA_NSS    8   // SPI chip select
  #define PIN_LORA_RST    12  // radio reset
  #define PIN_LORA_DIO1   14  // IRQ / DIO1
  #define PIN_LORA_BUSY   13  // BUSY flag
  #define PIN_LORA_SCK    9
  #define PIN_LORA_MOSI   10
  #define PIN_LORA_MISO   11

  // OLED SSD1306 (disabled by default to save power)
  #define PIN_OLED_SDA    17
  #define PIN_OLED_SCL    18
  #define PIN_OLED_RST    21

  // External sensor I2C bus (BME280, VEML7700 lux)
  // Uses a separate I2C port from the OLED to avoid address conflicts
  // and allow the OLED to be powered off independently.
  #define PIN_EXT_I2C_SDA  4
  #define PIN_EXT_I2C_SCL  5

  // Soil moisture – analog input (DFRobot SEN0308)
  // Wire through a voltage divider if sensor output exceeds 3.3 V.
  #define PIN_SOIL_MOISTURE  2

  // Sensor power rail – controls MOSFET that powers all external sensors.
  // Pull HIGH to enable sensor VCC, LOW to cut power.
  #define PIN_SENSOR_POWER  38

  // Battery voltage ADC divider
  // Heltec V3 has an onboard 100 kΩ / 100 kΩ divider on GPIO 1.
  // ADC reads Vbat/2.  For the VineGuard 12 V pack a separate external
  // divider with a larger ratio is required – see NODE_WIRING.md.
  #define PIN_BATTERY_ADC  1

  // Solar charger voltage ADC (optional, ENABLE_SOLAR_ADC=1)
  #define PIN_SOLAR_ADC    3

  // RS485 half-duplex UART for optional leaf wetness sensor
  #define PIN_RS485_TX     6
  #define PIN_RS485_RX     7
  #define PIN_RS485_DE     47  // Driver Enable (HIGH = transmit)

  // Status LED (active HIGH on Heltec V3)
  #define PIN_LED          35

  // User button (active LOW, also used as boot strap)
  #define PIN_BUTTON       0

#elif defined(BOARD_GENERIC_ESP32)

  // Generic ESP32 devkit – sensible defaults for breadboard prototyping
  #define PIN_LORA_NSS    5
  #define PIN_LORA_RST    14
  #define PIN_LORA_DIO1   2
  #define PIN_LORA_BUSY   4
  #define PIN_LORA_SCK    18
  #define PIN_LORA_MOSI   23
  #define PIN_LORA_MISO   19

  #define PIN_OLED_SDA    21
  #define PIN_OLED_SCL    22
  #define PIN_OLED_RST    -1  // not used

  #define PIN_EXT_I2C_SDA  21
  #define PIN_EXT_I2C_SCL  22

  #define PIN_SOIL_MOISTURE  34
  #define PIN_SENSOR_POWER   32
  #define PIN_BATTERY_ADC    35
  #define PIN_SOLAR_ADC      36

  #define PIN_RS485_TX   16
  #define PIN_RS485_RX   17
  #define PIN_RS485_DE   15

  #define PIN_LED        2
  #define PIN_BUTTON     0

#elif defined(BOARD_CUSTOM)
  // Define all PIN_* constants in your own pins_custom.h and include it here.
  #include "pins_custom.h"
#else
  #error "No board defined. Add -DBOARD_HELTEC_V3 or -DBOARD_GENERIC_ESP32 to build_flags."
#endif
