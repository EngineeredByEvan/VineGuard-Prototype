#pragma once

#include <cstdint>
#include <string>

struct TelemetryData {
    std::string version;
    std::string orgId;
    std::string siteId;
    std::string nodeId;
    uint64_t timestampMs;
    float soilMoisture;
    float soilTemperatureC;
    float ambientTemperatureC;
    float ambientHumidity;
    float lightLux;
    float batteryVoltage;
};

std::string buildTelemetryJson(const TelemetryData &data);
