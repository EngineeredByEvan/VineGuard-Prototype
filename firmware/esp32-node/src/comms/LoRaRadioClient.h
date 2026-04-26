#pragma once
#include "UplinkClient.h"

class LoRaRadioClient : public UplinkClient {
 public:
  bool begin() override;
  bool send(const String& payload) override;
  const char* modeName() const override { return "lora_p2p"; }
};
