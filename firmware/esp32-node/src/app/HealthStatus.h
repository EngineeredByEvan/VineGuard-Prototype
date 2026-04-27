#pragma once
#include <stdint.h>
#include <stddef.h>

// Aggregated runtime health flags.
// Populated by AppController each cycle, embedded in telemetry payload.

struct HealthStatus {
    bool    soilSensorOk        = false;
    bool    bme280Ok            = false;
    bool    luxSensorOk         = false;
    bool    leafWetnessOk       = false;
    bool    batteryOk           = false;
    bool    radioReady          = false;
    bool    lowBattery          = false;
    bool    criticalBattery     = false;
    int     failsafeQueueDepth  = 0;
    uint32_t bootCount          = 0;
    uint32_t uptimeSec          = 0;
    uint32_t sequence           = 0;
    int     lastRssi            = 0;
    float   lastSnr             = 0.0f;

    bool anySensorOk() const {
        return soilSensorOk || bme280Ok || luxSensorOk;
    }
};
