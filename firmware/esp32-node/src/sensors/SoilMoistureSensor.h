#pragma once
#include "SensorTypes.h"

class SoilMoistureSensor {
 public:
  explicit SoilMoistureSensor(int pin) : pin_(pin) {}
  bool begin();
  SoilReading read(int dryAdc, int wetAdc) const;
  static float mapToPercent(int raw, int dryAdc, int wetAdc);

 private:
  int pin_;
};
