#pragma once
// build_config.h — compile-time feature gates and defaults
// All flags can be overridden from platformio.ini build_flags.

// ─── Build mode (exactly one must be defined) ────────────────────────────────
// DEBUG_SERIAL_ONLY : read sensors (or mock), print JSON to Serial, no radio
// LORA_P2P          : compact JSON over raw LoRa to local gateway
// LORAWAN_OTAA      : LoRaWAN OTAA via RadioLib + US915, full network join

#if !defined(BUILD_MODE_DEBUG_SERIAL) && \
    !defined(BUILD_MODE_LORA_P2P)     && \
    !defined(BUILD_MODE_LORAWAN_OTAA)
  #define BUILD_MODE_DEBUG_SERIAL
  #warning "No BUILD_MODE defined — defaulting to DEBUG_SERIAL"
#endif

// ─── Mock sensors ────────────────────────────────────────────────────────────
// When defined, all sensor drivers return deterministic simulated readings.
// Realistic drift is applied each cycle so the dashboard shows useful data.
// #define MOCK_SENSORS  (set in platformio.ini per environment)

// ─── Optional hardware ───────────────────────────────────────────────────────
#ifndef ENABLE_LEAF_WETNESS
  #define ENABLE_LEAF_WETNESS 0
#endif

#ifndef ENABLE_OLED
  #define ENABLE_OLED 0
#endif

#ifndef ENABLE_SOLAR_ADC
  #define ENABLE_SOLAR_ADC 0
#endif

// ─── Deep sleep ──────────────────────────────────────────────────────────────
// 0 = polling loop (for debug), 1 = deep sleep between samples
#ifndef USE_DEEP_SLEEP
  #define USE_DEEP_SLEEP 0
#endif

// ─── Timing ──────────────────────────────────────────────────────────────────
// Interval between sensor samples (seconds)
#ifndef SAMPLE_INTERVAL_S
  #define SAMPLE_INTERVAL_S 900   // 15 min default
#endif

// Interval between LoRa uplinks (seconds).
// Must be >= SAMPLE_INTERVAL_S.  Set to a multiple to buffer readings.
#ifndef TRANSMIT_INTERVAL_S
  #define TRANSMIT_INTERVAL_S 900
#endif

// ─── Debug verbosity ─────────────────────────────────────────────────────────
// 0 = silent, 1 = errors + key events, 2 = verbose trace
#ifndef DEBUG_LEVEL
  #define DEBUG_LEVEL 1
#endif

// ─── LoRa radio defaults ─────────────────────────────────────────────────────
#define LORA_FREQUENCY_MHZ     915.0f
#define LORA_BANDWIDTH_KHZ     125.0f
#define LORA_SPREADING_FACTOR  9
#define LORA_CODING_RATE       7   // 4/7
#define LORA_TX_POWER_DBM      17
#define LORA_SYNC_WORD         0x12  // private network

// ─── LoRaWAN region ──────────────────────────────────────────────────────────
// US915 covers both the United States and Canada (902-928 MHz)
// Sub-band 2 (channels 8-15 + 65) is the most widely supported.
#define LORAWAN_SUBBAND 2

// ─── Firmware version (semver) ───────────────────────────────────────────────
#define FW_VERSION_MAJOR 0
#define FW_VERSION_MINOR 1
#define FW_VERSION_PATCH 0
#define FW_VERSION_STR   "0.1.0"

// ─── Payload schema ──────────────────────────────────────────────────────────
#define PAYLOAD_SCHEMA_VERSION "1.0"
// Compact LoRa P2P protocol identifier (binary mode)
#define VGPP_PROTOCOL_V1 0xA1
