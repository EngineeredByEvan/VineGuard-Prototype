#pragma once
// config.h — device identity and runtime-configurable parameters
//
// Build-time defaults live here.  Most values can be overridden at runtime
// from NVS via NvsConfigStore.  See docs/PROVISIONING.md for the full flow.

#include <Arduino.h>
#include "build_config.h"

// ─── Device identity (overridden from NVS after provisioning) ────────────────
#define DEFAULT_DEVICE_ID     "vineguard-node-000"
#define DEFAULT_NODE_SERIAL   "VG-000000"
#define DEFAULT_VINEYARD_ID   "unset"
#define DEFAULT_BLOCK_ID      "unset"
#define DEFAULT_NODE_TYPE     "basic"   // "basic" or "precision_plus"

// ─── Soil moisture ADC calibration (DFRobot SEN0308) ─────────────────────────
// Measure these per installation – see docs/NODE_WIRING.md.
// DRY_VALUE = ADC count in completely dry soil / in air
// WET_VALUE = ADC count in saturated soil / in water
#define SOIL_DRY_ADC_VALUE  2800
#define SOIL_WET_ADC_VALUE   800
#define SOIL_ADC_RESOLUTION 4096  // 12-bit ESP32 ADC

// ─── Battery / ADC ────────────────────────────────────────────────────────────
// Voltage divider ratio: ADC_in = Vbat / RATIO
// Heltec V3 onboard 100k/100k divider → ratio 2.0
// For external 12 V pack (100k + 11k divider) → ratio ≈ 10.09
#define BATTERY_DIVIDER_RATIO 2.0f
#define ADC_VREF_MV           3300

// 12 V Li-Ion (3S) pack thresholds
#define BATTERY_VOLTAGE_MAX          12.6f
#define BATTERY_VOLTAGE_MIN           9.0f
#define BATTERY_LOW_THRESHOLD_V       9.5f    // reduces transmit frequency
#define BATTERY_CRITICAL_THRESHOLD_V  9.1f   // skip radio entirely

// ─── Sensor I2C addresses ─────────────────────────────────────────────────────
#define BME280_I2C_ADDR   0x76   // SDO LOW=0x76, SDO HIGH=0x77
#define VEML7700_I2C_ADDR 0x10   // fixed

// ─── RS485 leaf wetness sensor (optional, ENABLE_LEAF_WETNESS=1) ──────────────
#define RS485_BAUD_RATE    9600
#define RS485_MODBUS_ADDR  1
#define RS485_TIMEOUT_MS   500

// ─── Sensor warm-up ───────────────────────────────────────────────────────────
// Delay (ms) after enabling sensor power rail before reading
#define SENSOR_WARMUP_MS 500

// ─── LoRa payload format ─────────────────────────────────────────────────────
#define PAYLOAD_FMT_JSON   0   // ~130-byte compact JSON
#define PAYLOAD_FMT_BINARY 1   // ~23-byte packed binary with CRC

#ifndef PAYLOAD_FORMAT
  #if defined(BUILD_MODE_LORAWAN_OTAA)
    #define PAYLOAD_FORMAT PAYLOAD_FMT_BINARY
  #else
    #define PAYLOAD_FORMAT PAYLOAD_FMT_JSON
  #endif
#endif

// ─── Failsafe queue ───────────────────────────────────────────────────────────
#define FAILSAFE_QUEUE_MAX_DEPTH 48   // 12 h backlog at 15-min intervals

// ─── OTA ─────────────────────────────────────────────────────────────────────
#define OTA_ENABLED 0
#define OTA_URL     ""

// ─── Canonical sensor readings struct ────────────────────────────────────────
struct SensorReadings {
    // Soil
    float  soilMoisturePercent  = -1.0f;
    int    soilMoistureRaw      = -1;
    float  soilVoltage          = -1.0f;
    float  soilTempC            = -1.0f;   // not wired in MVP

    // Environmental (BME280)
    float  ambientTempC         = -1.0f;
    float  ambientHumidityPct   = -1.0f;
    float  pressureHpa          = -1.0f;
    float  dewPointC            = -1.0f;   // computed from T+RH

    // Light (VEML7700)
    float  lightLux             = -1.0f;

    // Leaf wetness (precision+ only, ENABLE_LEAF_WETNESS=1)
    float  leafWetnessPercent   = -1.0f;
    int    leafWetnessRaw       = -1;

    // Power
    float  batteryVoltage       = -1.0f;
    int    batteryPercent       = -1;
    float  solarVoltage         = -1.0f;

    // Validity flags
    bool   soilOk               = false;
    bool   bme280Ok             = false;
    bool   luxOk                = false;
    bool   leafWetnessOk        = false;
    bool   batteryOk            = false;
};

// ─── Device config (loaded from NVS, defaults from above) ────────────────────
struct DeviceConfig {
    String   deviceId            = DEFAULT_DEVICE_ID;
    String   nodeSerial          = DEFAULT_NODE_SERIAL;
    String   vineyardId          = DEFAULT_VINEYARD_ID;
    String   blockId             = DEFAULT_BLOCK_ID;
    String   nodeType            = DEFAULT_NODE_TYPE;
    String   firmwareVersion     = FW_VERSION_STR;
    uint32_t sampleIntervalS     = SAMPLE_INTERVAL_S;
    uint32_t transmitIntervalS   = TRANSMIT_INTERVAL_S;
};
