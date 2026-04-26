#pragma once
#include <Arduino.h>

class UplinkClient {
 public:
  virtual ~UplinkClient() = default;
  virtual bool begin() = 0;
  virtual bool send(const String& payload) = 0;
  virtual const char* modeName() const = 0;
};
