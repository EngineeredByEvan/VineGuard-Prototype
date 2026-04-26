#include "LuxSensor.h"

#include <Arduino.h>
#include <Wire.h>

bool LuxSensor::begin() {
  // BH1750-compatible mode used by many I2C lux sensors.
  Wire.beginTransmission(0x23);
  present_ = (Wire.endTransmission() == 0);
  if (present_) {
    Wire.beginTransmission(0x23);
    Wire.write(0x10);
    Wire.endTransmission();
  }
  return present_;
}

LuxReading LuxSensor::read() const {
  LuxReading r;
  if (!present_) return r;
  Wire.beginTransmission(0x23);
  Wire.write(0x10);
  Wire.endTransmission();
  delay(180);
  Wire.requestFrom(0x23, 2);
  if (Wire.available() == 2) {
    uint16_t level = (Wire.read() << 8) | Wire.read();
    r.lux = level / 1.2f;
    r.ok = true;
  }
  return r;
}
