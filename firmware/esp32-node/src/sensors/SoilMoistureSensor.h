#pragma once
#include <Arduino.h>
#include "../util/Logger.h"
#include "../../include/config.h"
#include "SensorTypes.h"

// DFRobot SEN0308 capacitive waterproof soil moisture sensor.
// Output: analog voltage 0–3 V, inverse to moisture (dry=high, wet=low).

class SoilMoistureSensor {
public:
    SoilMoistureSensor(uint8_t pin,
                       int dryAdc = SOIL_DRY_ADC_VALUE,
                       int wetAdc = SOIL_WET_ADC_VALUE);

    void init();
    bool isPresent() const { return _present; }

    // Returns moisture percent (0–100).
    SensorResult readPercent();
    // Returns raw 12-bit ADC count.
    int readRaw();
    // Returns voltage at ADC pin (V).
    float readVoltage();

    void setCalibration(int dryAdc, int wetAdc);

private:
    uint8_t _pin;
    int     _dryAdc;
    int     _wetAdc;
    bool    _present = false;

    float adcToPercent(int raw) const;
};
