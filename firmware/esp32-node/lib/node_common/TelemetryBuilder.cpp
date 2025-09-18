#include "TelemetryBuilder.h"

#include <ArduinoJson.h>

std::string buildTelemetryJson(const TelemetryData &data) {
    StaticJsonDocument<512> doc;
    doc["version"] = data.version;
    doc["org"] = data.orgId;
    doc["site"] = data.siteId;
    doc["node"] = data.nodeId;
    doc["ts"] = data.timestampMs;

    JsonObject meas = doc.createNestedObject("measurements");
    meas["soilMoisture"] = data.soilMoisture;
    meas["soilTempC"] = data.soilTemperatureC;
    meas["ambientTempC"] = data.ambientTemperatureC;
    meas["ambientHumidity"] = data.ambientHumidity;
    meas["lightLux"] = data.lightLux;
    meas["batteryVoltage"] = data.batteryVoltage;

    std::string output;
    serializeJson(doc, output);
    return output;
}
