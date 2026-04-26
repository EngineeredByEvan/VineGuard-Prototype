#include "SerialDebugUplink.h"

bool SerialDebugUplink::begin() { return true; }
bool SerialDebugUplink::send(const String& payload) {
  Serial.println(payload);
  return true;
}
