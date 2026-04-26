#include "Bme280Sensor.h"

bool Bme280Sensor::begin() {
  present_ = bme_.begin(0x76) || bme_.begin(0x77);
  return present_;
}

AmbientReading Bme280Sensor::read() const {
  AmbientReading r;
  if (!present_) return r;
  r.tempC = bme_.readTemperature();
  r.humidityPct = bme_.readHumidity();
  r.pressureHpa = bme_.readPressure() / 100.0f;
  r.ok = true;
  return r;
}
