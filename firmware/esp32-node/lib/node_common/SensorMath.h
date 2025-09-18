#pragma once

#include <cstdint>

float normalizeSensorReading(uint16_t raw, uint16_t minValue, uint16_t maxValue);
float computeBatteryVoltage(uint16_t raw, uint16_t maxAdc, float referenceVoltage, float r1, float r2);
