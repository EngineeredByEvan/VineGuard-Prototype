#include "OtaUpdater.h"

#include <Arduino.h>

void OtaUpdater::check() {
  // MVP: disabled by default for LoRa-only deployments.
  Serial.println("[OTA] skipped (disabled)");
}
