#pragma once
// payload_schema.h — LoRa P2P binary payload layout constants
//
// VineGuard P2P Protocol v1 (VGPP-1)
// Used for compact LoRa P2P uplinks and LoRaWAN FPort 1 uplinks.
// The gateway decodes this into the V1 JSON schema sent to MQTT.
//
// See docs/PAYLOAD_CONTRACT.md for the full contract.

// ─── Binary frame format ─────────────────────────────────────────────────────
// All multi-byte fields are little-endian.
//
// Byte  Size  Field
//  0     1    PROTOCOL_ID (= 0xA1 for VGPP-1)
//  1     1    seq_lo  (sequence number low byte)
//  2     1    seq_hi  (sequence number high byte)
//  3     2    flags   (uint16, see FLAGS_* masks below)
//  5     2    soil_moisture_x100   (uint16, 0–10000 = 0.00–100.00 %)
//  7     2    soil_temp_encoded    (uint16, (°C + 40) × 10, 0–1200)
//  9     2    ambient_temp_encoded (uint16, (°C + 40) × 10)
// 11     2    ambient_humidity_x100 (uint16, 0–10000)
// 13     2    pressure_x10_m8500   (uint16, (hPa × 10) − 8500, 0–2500)
// 15     3    light_lux            (uint24 LE, 0–200 000)
// 18     1    battery_voltage_x10  (uint8, V × 10, 0–25.5 V)
// 19     1    battery_pct          (uint8, 0–100)
// [20    2    leaf_wetness_x100]   (present only if FLAGS_LEAF_WETNESS_VALID)
// [22    1    solar_voltage_x10]   (present only if FLAGS_SOLAR_VALID)
//  *     2    crc16_ccitt          (always last 2 bytes)
//
// Minimum frame: 22 bytes (no leaf wetness, no solar)
// With both optional fields: 25 bytes

#define VGPP_MIN_FRAME_LEN  22
#define VGPP_MAX_FRAME_LEN  25

// ─── flags bitfield ──────────────────────────────────────────────────────────
#define FLAGS_SOIL_VALID       (1 << 0)
#define FLAGS_SOIL_TEMP_VALID  (1 << 1)
#define FLAGS_BME280_VALID     (1 << 2)
#define FLAGS_LUX_VALID        (1 << 3)
#define FLAGS_LEAF_WETNESS_VALID (1 << 4)
#define FLAGS_SOLAR_VALID      (1 << 5)
#define FLAGS_TIER_PRECISION   (1 << 6)  // 0=basic, 1=precision_plus
#define FLAGS_LOW_BATTERY      (1 << 7)
#define FLAGS_SENSOR_ERROR     (1 << 8)  // any sensor failed to read
// Bits 9–15 reserved, must be zero.
