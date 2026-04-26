#pragma once
#include "SensorTypes.h"

class BatteryMonitor {
 public:
  BatteryMonitor(int batteryPin, int solarPin) : batteryPin_(batteryPin), solarPin_(solarPin) {}
  bool begin();
  BatteryReading read(float dividerRatio, float minV, float maxV, bool enableSolar) const;

 private:
  int batteryPin_;
  int solarPin_;
};
