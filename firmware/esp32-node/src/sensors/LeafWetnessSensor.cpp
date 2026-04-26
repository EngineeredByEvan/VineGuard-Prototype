#include "LeafWetnessSensor.h"

#include <Arduino.h>

bool LeafWetnessSensor::begin() {
#if ENABLE_LEAF_WETNESS
  present_ = true;
#else
  present_ = false;
#endif
  return present_;
}

LeafWetnessReading LeafWetnessSensor::read() {
  LeafWetnessReading r;
  if (!present_) return r;
  // TODO: Replace mock with actual RS485/Modbus command map for production sensor.
  mockRaw_ += random(-30, 25);
  if (mockRaw_ < 150) mockRaw_ = 150;
  if (mockRaw_ > 900) mockRaw_ = 900;
  r.raw = mockRaw_;
  r.percent = (mockRaw_ - 150) * 100.0f / 750.0f;
  r.wet = r.percent > 35.0f;
  r.ok = true;
  return r;
}
