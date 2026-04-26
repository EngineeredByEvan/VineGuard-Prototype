#include "SensorManager.h"

#include <Wire.h>

SensorManager::SensorManager(const RuntimeConfig& cfg)
    : cfg_(cfg),
      soil_(PIN_SOIL_ADC),
      battery_(PIN_BATTERY_ADC, PIN_SOLAR_ADC) {}

bool SensorManager::begin() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  soil_.begin();
  bme_.begin();
  lux_.begin();
  leaf_.begin();
  battery_.begin();
  return true;
}

SensorBundle SensorManager::sample() {
  SensorBundle b;
#if VINEGUARD_USE_MOCK_SENSORS
  static float soil = 30.0f;
  static float temp = 21.0f;
  static float hum = 62.0f;
  static float lux = 240.0f;
  soil += random(-12, 8) / 10.0f;
  temp += random(-5, 5) / 10.0f;
  hum += random(-10, 10) / 10.0f;
  lux += random(-90, 120) / 10.0f;
  soil = constrain(soil, 8.0f, 45.0f);
  hum = constrain(hum, 35.0f, 95.0f);
  lux = constrain(lux, 5.0f, 1400.0f);
  b.soil = {.ok = true, .raw = static_cast<int>(2200 - soil * 10), .voltage = 1.6f, .moisturePercent = soil};
  b.ambient = {.ok = true, .tempC = temp, .humidityPct = hum, .pressureHpa = 1012.5f};
  b.lux = {.ok = true, .lux = lux};
  b.leaf = leaf_.read();
  b.battery = {.ok = true, .batteryVoltage = 3.88f, .batteryPercent = 77, .lowBattery = false, .solarVoltage = 12.9f};
#else
  b.soil = soil_.read(cfg_.soilAdcDry, cfg_.soilAdcWet);
  b.ambient = bme_.read();
  b.lux = lux_.read();
  b.leaf = leaf_.read();
  b.battery = battery_.read(cfg_.batteryDividerRatio, cfg_.batteryMinV, cfg_.batteryMaxV, cfg_.enableSolarVoltage);
#endif
  return b;
}
