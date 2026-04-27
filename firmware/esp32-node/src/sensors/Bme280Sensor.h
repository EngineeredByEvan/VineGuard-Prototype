#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "../../include/config.h"
#include "../util/Logger.h"
#include "SensorTypes.h"

#ifndef NATIVE_TEST
  #include <Adafruit_BME280.h>
#endif

// BME280 temperature / humidity / pressure sensor via I2C.
// Mount in a radiation shield 15–30 cm from the main enclosure.

class Bme280Sensor {
public:
    explicit Bme280Sensor(TwoWire& wire = Wire, uint8_t addr = BME280_I2C_ADDR);

    bool init();
    bool isPresent() const { return _present; }

    struct Reading {
        float tempC    = -999.0f;
        float humidity = -1.0f;
        float pressure = -1.0f;
        float dewPoint = -999.0f;
        bool  ok       = false;
    };

    Reading read();

private:
    uint8_t   _addr;
    TwoWire&  _wire;
    bool      _present = false;

#ifndef NATIVE_TEST
    Adafruit_BME280 _bme;
#endif
};
