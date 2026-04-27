#pragma once
#include <Arduino.h>
#include "../../include/config.h"

// Pure-virtual interface for all uplink transports.
// AppController holds a pointer to an UplinkClient and calls send() without
// knowing whether it's Serial, LoRa P2P, LoRaWAN, or a test stub.

class UplinkClient {
public:
    virtual ~UplinkClient() = default;

    // One-time setup.  Returns false on fatal error (e.g. radio not found).
    virtual bool begin() = 0;

    // Send a pre-built JSON payload string.
    // Returns true when the message was accepted for delivery.
    // May queue internally if the channel is temporarily unavailable.
    virtual bool send(const char* jsonPayload, size_t len) = 0;

    // Returns true if the transport is currently available (radio joined, etc.)
    virtual bool isReady() const = 0;

    // Attempt to deliver any internally queued messages.
    // Call periodically even when no new data is available.
    virtual void flush() {}

    // Human-readable name for logging ("serial", "lora_p2p", "lorawan_otaa")
    virtual const char* name() const = 0;
};
