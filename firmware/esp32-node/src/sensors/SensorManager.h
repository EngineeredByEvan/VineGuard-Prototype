#pragma once

#include "config.h"
#include "sensors/BatteryMonitor.h"
#include "sensors/Bme280Sensor.h"
#include "sensors/LeafWetnessSensor.h"
#include "sensors/LuxSensor.h"
#include "sensors/SoilMoistureSensor.h"

class SensorManager {
 public:
  explicit SensorManager(const RuntimeConfig& cfg);
  bool begin();
  SensorBundle sample();

 private:
  const RuntimeConfig& cfg_;
  SoilMoistureSensor soil_;
  Bme280Sensor bme_;
  LuxSensor lux_;
  LeafWetnessSensor leaf_;
  BatteryMonitor battery_;
};
