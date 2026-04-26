#pragma once

struct HealthStatus {
  bool soilSensorOk = false;
  bool bme280Ok = false;
  bool luxSensorOk = false;
  bool leafWetnessOk = false;
  bool batteryOk = false;
  bool lowBattery = false;
  int failsafeQueueDepth = 0;
};
