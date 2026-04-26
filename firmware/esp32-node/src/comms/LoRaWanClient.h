#pragma once
#include "UplinkClient.h"

class LoRaWanClient : public UplinkClient {
 public:
  bool begin() override;
  bool send(const String& payload) override;
  const char* modeName() const override { return "lorawan_otaa"; }
};
