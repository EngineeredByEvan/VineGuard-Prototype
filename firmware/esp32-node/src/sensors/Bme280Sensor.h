#pragma once
#include <Adafruit_BME280.h>
#include "SensorTypes.h"

class Bme280Sensor {
 public:
  bool begin();
  AmbientReading read() const;
  bool isPresent() const { return present_; }

 private:
  Adafruit_BME280 bme_;
  bool present_ = false;
};
