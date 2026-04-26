#include "BatteryMonitor.h"

#include <Arduino.h>

bool BatteryMonitor::begin() {
  pinMode(batteryPin_, INPUT);
  pinMode(solarPin_, INPUT);
  return true;
}

BatteryReading BatteryMonitor::read(float dividerRatio, float minV, float maxV, bool enableSolar) const {
  BatteryReading b;
  int raw = analogRead(batteryPin_);
  b.batteryVoltage = (3.3f * static_cast<float>(raw) / 4095.0f) * dividerRatio;
  float pct = ((b.batteryVoltage - minV) / (maxV - minV)) * 100.0f;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  b.batteryPercent = static_cast<int>(pct + 0.5f);
  b.lowBattery = b.batteryVoltage < 3.45f;
  if (enableSolar) {
    int solarRaw = analogRead(solarPin_);
    b.solarVoltage = (3.3f * static_cast<float>(solarRaw) / 4095.0f) * dividerRatio * 4.0f;
  }
  b.ok = true;
  return b;
}
