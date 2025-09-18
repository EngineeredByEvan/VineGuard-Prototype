#include "SensorMath.h"

#include <algorithm>

float normalizeSensorReading(uint16_t raw, uint16_t minValue, uint16_t maxValue) {
    if (minValue == maxValue) {
        return 0.0f;
    }
    if (minValue > maxValue) {
        std::swap(minValue, maxValue);
    }
    if (raw <= minValue) {
        return 0.0f;
    }
    if (raw >= maxValue) {
        return 1.0f;
    }
    const float span = static_cast<float>(maxValue - minValue);
    const float normalized = (static_cast<float>(raw - minValue) / span);
    return std::clamp(normalized, 0.0f, 1.0f);
}

float computeBatteryVoltage(uint16_t raw, uint16_t maxAdc, float referenceVoltage, float r1, float r2) {
    if (maxAdc == 0 || referenceVoltage <= 0.0f || r2 <= 0.0f) {
        return 0.0f;
    }
    const float voltageAtPin = (static_cast<float>(raw) / static_cast<float>(maxAdc)) * referenceVoltage;
    const float dividerRatio = (r1 + r2) / r2;
    return voltageAtPin * dividerRatio;
}
