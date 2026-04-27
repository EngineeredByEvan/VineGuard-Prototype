#include "TelemetryBuilder.h"
#include <math.h>

#ifndef NATIVE_TEST
  #include <Arduino.h>
#else
  #include <cstdint>
  // Minimal millis() stub for native tests
  static uint32_t millis() { return 0; }
#endif

// Helper: return v if it is a valid reading, otherwise serialise as JSON null.
// We cannot directly write NULL into ArduinoJson without a JsonVariant trick,
// so callers check sentinel before adding the field.
float TelemetryBuilder::nullableFloat(float v, float sentinel) {
    return (v <= sentinel) ? NAN : v;
}

size_t TelemetryBuilder::buildV1Json(const DeviceConfig&  cfg,
                                      const SensorReadings& r,
                                      const HealthStatus&   h,
                                      char*                 buf,
                                      size_t                bufSize) {
    StaticJsonDocument<768> doc;

    doc["schema_version"] = PAYLOAD_SCHEMA_VERSION;
    doc["device_id"]      = cfg.deviceId.c_str();
    doc["gateway_id"]     = (const char*)nullptr;   // filled by gateway
    doc["timestamp"]      = (uint32_t)(millis() / 1000);  // uptime proxy; gateway adds wall clock
    doc["tier"]           = cfg.nodeType.c_str();

    JsonObject sensors = doc.createNestedObject("sensors");
    if (r.soilOk)   sensors["soil_moisture_pct"] = round(r.soilMoisturePercent * 10.0f) / 10.0f;
    else            sensors["soil_moisture_pct"] = (const char*)nullptr;

    // soil_temp_c is reserved for a future probe – always null for MVP
    sensors["soil_temp_c"] = (const char*)nullptr;

    if (r.bme280Ok) {
        sensors["ambient_temp_c"]       = round(r.ambientTempC * 10.0f) / 10.0f;
        sensors["ambient_humidity_pct"] = round(r.ambientHumidityPct * 10.0f) / 10.0f;
        sensors["pressure_hpa"]         = round(r.pressureHpa * 10.0f) / 10.0f;
    } else {
        sensors["ambient_temp_c"]       = (const char*)nullptr;
        sensors["ambient_humidity_pct"] = (const char*)nullptr;
        sensors["pressure_hpa"]         = (const char*)nullptr;
    }

    if (r.luxOk)         sensors["light_lux"]        = (int)r.lightLux;
    else                 sensors["light_lux"]         = (const char*)nullptr;

    if (r.leafWetnessOk) sensors["leaf_wetness_pct"] = round(r.leafWetnessPercent * 10.0f) / 10.0f;
    else                 sensors["leaf_wetness_pct"] = (const char*)nullptr;

    JsonObject meta = doc.createNestedObject("meta");
    if (r.batteryOk) {
        meta["battery_voltage"] = round(r.batteryVoltage * 100.0f) / 100.0f;
        meta["battery_pct"]     = r.batteryPercent;
    } else {
        meta["battery_voltage"] = (const char*)nullptr;
        meta["battery_pct"]     = (const char*)nullptr;
    }

    // RSSI/SNR filled by gateway or LoRaWAN network server
    meta["rssi"] = (const char*)nullptr;
    meta["snr"]  = (const char*)nullptr;
    meta["sensor_ok"] = h.anySensorOk();

    // Extended fields (parsed by gateway; ingestor ignores unknown fields)
    doc["firmware_version"]     = cfg.firmwareVersion.c_str();
    doc["vineyard_id"]          = cfg.vineyardId.c_str();
    doc["block_id"]             = cfg.blockId.c_str();
    doc["sequence"]             = h.sequence;
    doc["uptime_sec"]           = h.uptimeSec;
    doc["boot_count"]           = h.bootCount;
    doc["queue_depth"]          = h.failsafeQueueDepth;

    if (r.bme280Ok) doc["dew_point_c"] = round(r.dewPointC * 10.0f) / 10.0f;

#if ENABLE_SOLAR_ADC
    if (r.solarVoltage >= 0.0f) doc["solar_voltage"] = round(r.solarVoltage * 100.0f) / 100.0f;
#endif

    size_t written = serializeJson(doc, buf, bufSize);
    return written;
}

size_t TelemetryBuilder::buildCompactJson(const DeviceConfig&  cfg,
                                           const SensorReadings& r,
                                           const HealthStatus&   h,
                                           char*                 buf,
                                           size_t                bufSize) {
    // Compact format for LoRa P2P – abbreviated keys, flat structure, ~130 bytes.
    // Key map (must match edge/gateway/src/vineguard_gateway/decoder.py COMPACT_KEY_MAP):
    //   v  = schema version
    //   id = device_id
    //   seq= sequence
    //   sm = soil_moisture_pct
    //   at = ambient_temp_c
    //   ah = ambient_humidity_pct
    //   p  = pressure_hpa
    //   l  = light_lux
    //   lw = leaf_wetness_pct
    //   bv = battery_voltage
    //   bp = battery_pct
    //   sv = solar_voltage
    //   ok = sensor_ok (0/1)

    StaticJsonDocument<384> doc;

    doc["v"]   = 1;
    doc["id"]  = cfg.deviceId.c_str();
    doc["seq"] = h.sequence;

    if (r.soilOk)         doc["sm"]  = round(r.soilMoisturePercent * 10.0f) / 10.0f;
    if (r.bme280Ok) {
        doc["at"] = round(r.ambientTempC * 10.0f) / 10.0f;
        doc["ah"] = round(r.ambientHumidityPct * 10.0f) / 10.0f;
        doc["p"]  = (int)r.pressureHpa;
    }
    if (r.luxOk)          doc["l"]   = (int)r.lightLux;
    if (r.leafWetnessOk)  doc["lw"]  = round(r.leafWetnessPercent * 10.0f) / 10.0f;
    if (r.batteryOk) {
        doc["bv"] = round(r.batteryVoltage * 100.0f) / 100.0f;
        doc["bp"] = r.batteryPercent;
    }
#if ENABLE_SOLAR_ADC
    if (r.solarVoltage >= 0.0f) doc["sv"] = round(r.solarVoltage * 10.0f) / 10.0f;
#endif
    doc["ok"]  = h.anySensorOk() ? 1 : 0;
    doc["tier"]= cfg.nodeType.c_str();

    size_t written = serializeJson(doc, buf, bufSize);
    return written;
}
