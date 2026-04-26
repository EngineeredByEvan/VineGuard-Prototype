#include "SoilMoistureSensor.h"

#include <Arduino.h>

bool SoilMoistureSensor::begin() {
  pinMode(pin_, INPUT);
  return true;
}

float SoilMoistureSensor::mapToPercent(int raw, int dryAdc, int wetAdc) {
  if (dryAdc == wetAdc) return 0;
  float pct = (static_cast<float>(dryAdc - raw) / static_cast<float>(dryAdc - wetAdc)) * 100.0f;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

SoilReading SoilMoistureSensor::read(int dryAdc, int wetAdc) const {
  SoilReading r;
  r.raw = analogRead(pin_);
  r.voltage = (3.3f * static_cast<float>(r.raw)) / 4095.0f;
  r.moisturePercent = mapToPercent(r.raw, dryAdc, wetAdc);
  r.ok = true;
  return r;
}
