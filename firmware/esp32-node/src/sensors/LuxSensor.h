#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "../../include/config.h"
#include "../util/Logger.h"
#include "SensorTypes.h"

#ifndef NATIVE_TEST
  #include <Adafruit_VEML7700.h>
#endif

// DFRobot SEN0390 canopy light sensor (VEML7700 chip, I2C address 0x10).
// Mount on a 1–2 m cable under or inside the canopy row.

class LuxSensor {
public:
    explicit LuxSensor(TwoWire& wire = Wire);

    bool init();
    bool isPresent() const { return _present; }

    SensorResult readLux();

private:
    TwoWire& _wire;
    bool     _present = false;

#ifndef NATIVE_TEST
    Adafruit_VEML7700 _veml;
#endif
};
