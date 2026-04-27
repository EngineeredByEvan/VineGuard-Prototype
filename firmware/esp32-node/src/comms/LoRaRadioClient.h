#pragma once
#include "UplinkClient.h"
#include "../../include/pins.h"
#include "../../include/build_config.h"
#include "../../include/payload_schema.h"
#include "../util/Logger.h"
#include "../util/Crc.h"

#ifndef NATIVE_TEST
  #include <RadioLib.h>
#endif

// LoRa P2P uplink using RadioLib SX1262.
// Sends compact JSON payload (PAYLOAD_FMT_JSON) or binary (PAYLOAD_FMT_BINARY)
// over raw LoRa at 915 MHz to the local VineGuard gateway.
// No network join required.

class LoRaRadioClient : public UplinkClient {
public:
    bool begin()                                     override;
    bool send(const char* jsonPayload, size_t len)   override;
    bool isReady() const                             override { return _ready; }
    const char* name() const                         override { return "lora_p2p"; }

    // Last measured RSSI/SNR (populated after receive window, if any)
    int   lastRssi() const { return _lastRssi; }
    float lastSnr()  const { return _lastSnr;  }

private:
    bool  _ready    = false;
    int   _lastRssi = 0;
    float _lastSnr  = 0.0f;

#ifndef NATIVE_TEST
    SX1262 _radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1,
                               PIN_LORA_RST, PIN_LORA_BUSY);
#endif

    bool initRadio();
    bool transmitJson(const char* json, size_t len);
};
