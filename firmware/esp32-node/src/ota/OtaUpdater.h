#pragma once
#include <Arduino.h>
#include "../../include/build_config.h"
#include "../util/Logger.h"

// OTA firmware update support.
//
// For LoRa-only nodes OTA over LoRa is out of scope for MVP.
// Wi-Fi OTA via HTTPS is stub-implemented here; enable by setting
// OTA_ENABLED=1 and OTA_URL in config.h when a Wi-Fi-equipped gateway
// or local AP is available during the maintenance window.
//
// See docs/OTA_STRATEGY.md for the full OTA approach.

class OtaUpdater {
public:
    // Returns true if a new firmware version is available and should be applied.
    // Only call when Wi-Fi is connected and battery is above LOW threshold.
    bool checkAndApply();

    // True if OTA is enabled AND Wi-Fi credentials are configured.
    bool isEnabled() const { return OTA_ENABLED && (OTA_URL[0] != '\0'); }
};
