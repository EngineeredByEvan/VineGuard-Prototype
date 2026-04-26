#pragma once

#include <Arduino.h>

struct SoilReading {
  bool ok = false;
  int raw = 0;
  float voltage = 0;
  float moisturePercent = 0;
};

struct AmbientReading {
  bool ok = false;
  float tempC = NAN;
  float humidityPct = NAN;
  float pressureHpa = NAN;
};

struct LuxReading {
  bool ok = false;
  float lux = NAN;
};

struct LeafWetnessReading {
  bool ok = false;
  int raw = 0;
  float percent = NAN;
  bool wet = false;
};

struct BatteryReading {
  bool ok = false;
  float batteryVoltage = NAN;
  int batteryPercent = -1;
  bool lowBattery = false;
  float solarVoltage = NAN;
};

struct SensorBundle {
  SoilReading soil;
  AmbientReading ambient;
  LuxReading lux;
  LeafWetnessReading leaf;
  BatteryReading battery;
};
