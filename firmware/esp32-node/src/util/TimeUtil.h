#pragma once
#include <stdint.h>
#include <stddef.h>

namespace TimeUtil {
    // Format millisecond uptime as "DDd HH:MM:SS"
    void formatUptime(uint32_t uptimeSec, char* buf, size_t bufLen);

    // Compute dew point (°C) from temperature (°C) and relative humidity (%)
    // Uses the simplified Magnus approximation (accurate to ±0.35 °C)
    float dewPoint(float tempC, float rhPct);

    // Map a 12V Li-Ion pack voltage to estimated SoC percent (0-100)
    int batteryPercentFromVoltage(float volts, float vMin, float vMax);
}
