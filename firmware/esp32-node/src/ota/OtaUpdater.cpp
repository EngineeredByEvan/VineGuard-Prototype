#include "OtaUpdater.h"

static const char* TAG = "OTA";

bool OtaUpdater::checkAndApply() {
    if (!isEnabled()) {
        LOG_DBG(TAG, "OTA disabled");
        return false;
    }

    // TODO (future work): implement HTTPS OTA check.
    // 1. Connect to OTA_URL, fetch version manifest JSON.
    // 2. Compare manifest.firmware_version with FW_VERSION_STR.
    // 3. If newer, download binary and call Update.begin() / Update.write() / Update.end().
    // 4. Validate SHA256 checksum before applying.
    // 5. Reject if battery below LOW threshold.
    // 6. Reboot after successful update.
    //
    // Reference: ESP32 Arduino OTA library (esp_https_ota.h or ArduinoOTA)
    // See docs/OTA_STRATEGY.md.
    LOG_INFO(TAG, "OTA check stub – not yet implemented (LoRa-only MVP)");
    return false;
}
