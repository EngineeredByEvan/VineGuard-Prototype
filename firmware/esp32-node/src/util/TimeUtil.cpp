#include "TimeUtil.h"
#include <math.h>
#include <stdio.h>

void TimeUtil::formatUptime(uint32_t uptimeSec, char* buf, size_t bufLen) {
    uint32_t d = uptimeSec / 86400;
    uint32_t h = (uptimeSec % 86400) / 3600;
    uint32_t m = (uptimeSec % 3600) / 60;
    uint32_t s = uptimeSec % 60;
    if (d > 0) {
        snprintf(buf, bufLen, "%ud %02u:%02u:%02u", (unsigned)d, (unsigned)h, (unsigned)m, (unsigned)s);
    } else {
        snprintf(buf, bufLen, "%02u:%02u:%02u", (unsigned)h, (unsigned)m, (unsigned)s);
    }
}

float TimeUtil::dewPoint(float tempC, float rhPct) {
    // Simplified Magnus: Td ≈ T − ((100 − RH) / 5)
    return tempC - ((100.0f - rhPct) / 5.0f);
}

int TimeUtil::batteryPercentFromVoltage(float volts, float vMin, float vMax) {
    if (volts <= vMin) return 0;
    if (volts >= vMax) return 100;
    float pct = (volts - vMin) / (vMax - vMin) * 100.0f;
    return (int)(pct + 0.5f);
}
