#pragma once
#include <ArduinoJson.h>

#include "app/HealthStatus.h"
#include "config.h"
#include "sensors/SensorTypes.h"

class TelemetryBuilder {
 public:
  static String buildLegacyFlatJson(const RuntimeConfig& cfg, const SensorBundle& s);
  static String buildEnhancedJson(const RuntimeConfig& cfg, const SensorBundle& s, const HealthStatus& h,
                                  uint32_t sequence, uint32_t bootCount, uint32_t uptimeSec,
                                  const char* radioMode);
};
