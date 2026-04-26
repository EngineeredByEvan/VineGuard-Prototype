#include "LoRaWanClient.h"

#include <Arduino.h>

bool LoRaWanClient::begin() {
  // TODO: OTAA join with RadioLib LoRaWAN using lorawan_keys.h
  return false;
}

bool LoRaWanClient::send(const String& payload) {
  (void)payload;
  return false;
}
