#include "LoRaRadioClient.h"

#include <Arduino.h>

bool LoRaRadioClient::begin() {
  // TODO: integrate RadioLib SX1262 init for Heltec/DIYmall ESP32-S3 LoRa boards.
  return true;
}

bool LoRaRadioClient::send(const String& payload) {
  Serial.println("[LORA_P2P_TX] " + payload);
  // TODO: replace with radio transmit
  return true;
}
