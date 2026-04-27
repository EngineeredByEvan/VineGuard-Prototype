#pragma once
#include "UplinkClient.h"
#include "../util/Logger.h"

// Writes the full JSON payload to Serial.
// Used in DEBUG_SERIAL_ONLY builds and as a fallback channel when radio fails.
// The gateway can receive these via USB serial in serial_json mode.

class SerialDebugUplink : public UplinkClient {
public:
    bool begin()                                     override;
    bool send(const char* jsonPayload, size_t len)   override;
    bool isReady() const                             override { return true; }
    const char* name() const                         override { return "serial"; }
};
