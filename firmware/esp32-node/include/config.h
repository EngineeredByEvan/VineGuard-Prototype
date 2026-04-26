#pragma once

#include <Arduino.h>

#include "build_config.h"
#include "pins.h"
#include "payload_schema.h"

struct DeviceIdentity {
  String deviceId = "vg-node-001";
  String nodeSerial = "VG-DEV-001";
  String vineyardId = "vineyard-demo";
  String blockId = "block-demo";
  String nodeType = "basic";
};

struct RuntimeConfig {
  DeviceIdentity identity;
  uint32_t sampleIntervalSec = SAMPLE_INTERVAL_MIN * 60;
  uint32_t transmitIntervalSec = TRANSMIT_INTERVAL_MIN * 60;
  int soilAdcDry = 2900;
  int soilAdcWet = 1400;
  float batteryMinV = 3.25f;
  float batteryMaxV = 4.20f;
  float batteryDividerRatio = 2.0f;
  bool enableSolarVoltage = true;
};
