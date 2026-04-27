#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "../../include/config.h"
#include "../../include/pins.h"
#include "SoilMoistureSensor.h"
#include "Bme280Sensor.h"
#include "LuxSensor.h"
#include "LeafWetnessSensor.h"
#include "BatteryMonitor.h"
#include "../util/Logger.h"

// SensorManager coordinates all sensor drivers.
// Handles power rail switching, warm-up delay, and populates SensorReadings.

class SensorManager {
public:
    SensorManager();

    // Call once at first boot (or after reset).
    void begin();

    // Power on sensor rail, read all enabled sensors, power off rail.
    // Returns false if a critical sensor (BME280) is missing.
    bool sample(SensorReadings& out);

    // Individual sensor presence after begin()
    bool soilPresent()       const;
    bool bme280Present()     const;
    bool luxPresent()        const;
    bool leafWetnessPresent() const;

private:
    SoilMoistureSensor _soil;
    Bme280Sensor       _bme;
    LuxSensor          _lux;
    BatteryMonitor     _battery;

#if ENABLE_LEAF_WETNESS
    LeafWetnessSensor  _leaf;
#endif

    void powerOn();
    void powerOff();
};
