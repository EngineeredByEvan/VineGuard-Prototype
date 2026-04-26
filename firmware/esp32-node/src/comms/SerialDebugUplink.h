#pragma once
#include "UplinkClient.h"

class SerialDebugUplink : public UplinkClient {
 public:
  bool begin() override;
  bool send(const String& payload) override;
  const char* modeName() const override { return "serial_debug"; }
};
