#include "TelemetryBuilder.h"

#include <time.h>

String TelemetryBuilder::buildLegacyFlatJson(const RuntimeConfig& cfg, const SensorBundle& s) {
  StaticJsonDocument<384> d;
  d["deviceId"] = cfg.identity.deviceId;
  d["soilMoisture"] = s.soil.moisturePercent;
  d["soilTempC"] = nullptr;
  d["ambientTempC"] = s.ambient.ok ? s.ambient.tempC : nullptr;
  d["ambientHumidity"] = s.ambient.ok ? s.ambient.humidityPct : nullptr;
  d["lightLux"] = s.lux.ok ? s.lux.lux : nullptr;
  d["batteryVoltage"] = s.battery.batteryVoltage;
  d["timestamp"] = static_cast<unsigned long>(time(nullptr));
  String out;
  serializeJson(d, out);
  return out;
}

String TelemetryBuilder::buildEnhancedJson(const RuntimeConfig& cfg, const SensorBundle& s, const HealthStatus& h,
                                           uint32_t sequence, uint32_t bootCount, uint32_t uptimeSec,
                                           const char* radioMode) {
  StaticJsonDocument<1024> d;
  d["schema_version"] = "1.0";
  d["device_id"] = cfg.identity.deviceId;
  d["tier"] = cfg.identity.nodeType;
  d["timestamp"] = static_cast<unsigned long>(time(nullptr));

  JsonObject sensors = d.createNestedObject("sensors");
  sensors["soil_moisture_pct"] = s.soil.moisturePercent;
  sensors["soil_temp_c"] = nullptr;
  sensors["ambient_temp_c"] = s.ambient.ok ? s.ambient.tempC : nullptr;
  sensors["ambient_humidity_pct"] = s.ambient.ok ? s.ambient.humidityPct : nullptr;
  sensors["pressure_hpa"] = s.ambient.ok ? s.ambient.pressureHpa : nullptr;
  sensors["light_lux"] = s.lux.ok ? s.lux.lux : nullptr;
  sensors["leaf_wetness_pct"] = s.leaf.ok ? s.leaf.percent : nullptr;

  JsonObject meta = d.createNestedObject("meta");
  meta["battery_voltage"] = s.battery.batteryVoltage;
  meta["battery_pct"] = s.battery.batteryPercent;
  meta["rssi"] = nullptr;
  meta["snr"] = nullptr;
  meta["sensor_ok"] = h.soilSensorOk && h.bme280Ok && h.luxSensorOk && h.batteryOk;

  JsonObject ext = d.createNestedObject("vineguard");
  ext["schemaVersion"] = SCHEMA_VERSION;
  ext["firmwareVersion"] = FW_VERSION;
  ext["nodeType"] = cfg.identity.nodeType;
  ext["vineyardId"] = cfg.identity.vineyardId;
  ext["blockId"] = cfg.identity.blockId;
  ext["sequence"] = sequence;
  ext["bootCount"] = bootCount;
  ext["uptimeSec"] = uptimeSec;
  ext["radioMode"] = radioMode;
  ext["failsafeQueueDepth"] = h.failsafeQueueDepth;

  String out;
  serializeJson(d, out);
  return out;
}
