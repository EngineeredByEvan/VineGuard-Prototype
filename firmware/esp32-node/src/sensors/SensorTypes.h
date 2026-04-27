#pragma once
#include <stdint.h>

// Common enums and result types for sensor drivers.

enum class SensorStatus : uint8_t {
    OK        = 0,
    NOT_FOUND = 1,   // I2C/UART device not detected at boot
    READ_ERR  = 2,   // present but read returned an error
    TIMEOUT   = 3,   // RS485 / serial read timeout
    DISABLED  = 4,   // not compiled in (ENABLE_* = 0)
    MOCK      = 5,   // MOCK_SENSORS mode, simulated value
};

struct SensorResult {
    float  value  = 0.0f;
    SensorStatus status = SensorStatus::NOT_FOUND;
    bool   ok() const { return status == SensorStatus::OK || status == SensorStatus::MOCK; }
};
