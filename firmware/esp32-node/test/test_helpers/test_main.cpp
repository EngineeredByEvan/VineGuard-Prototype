#include <ArduinoJson.h>
#include <cassert>
#include <cmath>
#include <string>

#include "SensorMath.h"
#include "TelemetryBuilder.h"

static bool nearlyEqual(float a, float b, float epsilon = 0.001f) {
    return std::fabs(a - b) <= epsilon;
}

int main() {
    // normalizeSensorReading tests
    assert(nearlyEqual(normalizeSensorReading(0, 0, 4095), 0.0f));
    assert(nearlyEqual(normalizeSensorReading(4095, 0, 4095), 1.0f));
    assert(nearlyEqual(normalizeSensorReading(2048, 0, 4095), 0.5f, 0.01f));
    assert(nearlyEqual(normalizeSensorReading(2048, 3000, 1000), 0.5f, 0.01f));
    assert(nearlyEqual(normalizeSensorReading(5000, 0, 4095), 1.0f));

    const float voltage = computeBatteryVoltage(2048, 4095, 3.3f, 100000.0f, 10000.0f);
    assert(nearlyEqual(voltage, 6.63f, 0.1f));

    TelemetryData data{
        .version = "0.1.0",
        .orgId = "org",
        .siteId = "site",
        .nodeId = "node",
        .timestampMs = 123456789ULL,
        .soilMoisture = 0.42f,
        .soilTemperatureC = 19.5f,
        .ambientTemperatureC = 21.1f,
        .ambientHumidity = 56.0f,
        .lightLux = 123.4f,
        .batteryVoltage = 3.71f,
    };

    std::string json = buildTelemetryJson(data);

    StaticJsonDocument<512> doc;
    auto err = deserializeJson(doc, json);
    assert(err == DeserializationError::Ok);
    assert(std::string(doc["version"]) == "0.1.0");
    assert(std::string(doc["org"]) == "org");
    assert(std::string(doc["site"]) == "site");
    assert(std::string(doc["node"]) == "node");
    assert(doc["ts"].as<uint64_t>() == 123456789ULL);

    JsonObject meas = doc["measurements"];
    assert(nearlyEqual(meas["soilMoisture"].as<float>(), 0.42f, 0.001f));
    assert(nearlyEqual(meas["soilTempC"].as<float>(), 19.5f, 0.001f));
    assert(nearlyEqual(meas["ambientTempC"].as<float>(), 21.1f, 0.001f));
    assert(nearlyEqual(meas["ambientHumidity"].as<float>(), 56.0f, 0.001f));
    assert(nearlyEqual(meas["lightLux"].as<float>(), 123.4f, 0.001f));
    assert(nearlyEqual(meas["batteryVoltage"].as<float>(), 3.71f, 0.001f));

    return 0;
}
