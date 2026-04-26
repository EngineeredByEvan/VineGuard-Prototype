#pragma once
#include "SensorTypes.h"

class LuxSensor {
 public:
  bool begin();
  LuxReading read() const;
  bool isPresent() const { return present_; }

 private:
  bool present_ = false;
};
