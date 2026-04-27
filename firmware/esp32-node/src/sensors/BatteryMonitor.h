#pragma once
#include <Arduino.h>
#include "../../include/config.h"
#include "../util/Logger.h"
#include "SensorTypes.h"

// Battery and optional solar voltage monitoring via ADC voltage divider.
// Designed for a 12 V Li-Ion pack (3S) with a resistor divider on the ADC pin.

class BatteryMonitor {
public:
    BatteryMonitor(uint8_t battPin,
                   float   dividerRatio = BATTERY_DIVIDER_RATIO,
                   float   vMin         = BATTERY_VOLTAGE_MIN,
                   float   vMax         = BATTERY_VOLTAGE_MAX,
                   uint8_t solarPin     = 0xFF);

    void init();

    struct Reading {
        float battVoltage = 0.0f;
        int   battPercent = 0;
        float solarVoltage = 0.0f;   // -1 if not configured
        bool  lowBattery  = false;
        bool  critical    = false;
        bool  ok          = false;
    };

    Reading read();

private:
    uint8_t _battPin;
    uint8_t _solarPin;
    float   _dividerRatio;
    float   _vMin;
    float   _vMax;

    float adcToVoltage(int raw) const;
};
