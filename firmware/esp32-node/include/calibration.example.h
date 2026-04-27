#pragma once
// calibration.example.h — per-node sensor calibration values
//
// INSTRUCTIONS:
//  1. Copy this file to calibration.local.h in the same directory.
//  2. Fill in values measured during bench test and field installation.
//  3. calibration.local.h is listed in .gitignore and will NOT be committed.
//
// If calibration.local.h is absent the firmware falls back to the
// compile-time defaults in config.h.

// ─── Soil moisture (DFRobot SEN0308 capacitive sensor) ───────────────────────
// Procedure:
//  1. Connect sensor, run DEBUG_SERIAL build, open serial monitor.
//  2. Hold sensor in dry air for 30 s, note the raw ADC value → SOIL_DRY
//  3. Submerge sensor tip in clean water for 30 s, note ADC value → SOIL_WET
//
// Note: higher ADC = drier soil for this sensor type.
#define CAL_SOIL_DRY_ADC  2800   // air/dry reading
#define CAL_SOIL_WET_ADC   800   // saturated/water reading

// ─── Battery voltage divider (override if you changed the resistors) ──────────
// Ratio = (R_top + R_bottom) / R_bottom
// Heltec V3 onboard: 100 kΩ + 100 kΩ → ratio = 2.0
// External 12 V divider example: 100 kΩ + 11 kΩ → ratio ≈ 10.09
#define CAL_BATTERY_DIVIDER_RATIO  2.0f

// ─── Light / lux calibration ──────────────────────────────────────────────────
// VEML7700 has hardware gain and integration time settings that affect the
// raw lux reading.  The Adafruit library auto-ranges; no manual cal needed
// for typical use.  Set a scale factor here if your sensor reads consistently
// high or low vs. a reference meter.
#define CAL_LUX_SCALE_FACTOR  1.0f

// ─── Reference lux (for canopy light % calculation) ───────────────────────────
// Maximum expected lux at the sensor location on a clear mid-day.
// Set to 0 to disable canopy % calculation (gateway will use block setting).
#define CAL_REFERENCE_LUX_PEAK  0.0f
