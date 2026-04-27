#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "../../include/config.h"
#include "../../include/build_config.h"
#include "HealthStatus.h"

// Builds the V1 JSON telemetry payload that matches the VineGuard cloud schema.
// Output is the same format the simulator publishes, so the existing ingestor,
// analytics, and dashboard work without any cloud-side changes.
//
// Compact LoRa JSON variant (for P2P mode) uses abbreviated field names and
// omits the nested structure; the gateway expands it back to V1 before MQTT.

class TelemetryBuilder {
public:
    // Build the full V1 JSON payload.
    // Returns the number of bytes written to buf (excluding null terminator).
    // buf should be at least 512 bytes.
    static size_t buildV1Json(const DeviceConfig&  cfg,
                               const SensorReadings& readings,
                               const HealthStatus&   health,
                               char*                 buf,
                               size_t                bufSize);

    // Build a compact LoRa P2P JSON payload (~130 bytes).
    // Field names are abbreviated; the gateway decodes using COMPACT_KEY_MAP.
    static size_t buildCompactJson(const DeviceConfig&  cfg,
                                   const SensorReadings& readings,
                                   const HealthStatus&   health,
                                   char*                 buf,
                                   size_t                bufSize);
private:
    static float nullableFloat(float v, float sentinel = -1.0f);
};
