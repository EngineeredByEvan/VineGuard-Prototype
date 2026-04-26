#pragma once
#include "SensorTypes.h"

class LeafWetnessSensor {
 public:
  bool begin();
  LeafWetnessReading read();
  bool isPresent() const { return present_; }

 private:
  bool present_ = false;
  int mockRaw_ = 450;
};
