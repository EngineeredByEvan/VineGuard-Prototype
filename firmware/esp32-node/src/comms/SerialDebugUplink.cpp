#include "SerialDebugUplink.h"

bool SerialDebugUplink::begin() {
    // Serial is already initialised by Logger::init()
    return true;
}

bool SerialDebugUplink::send(const char* jsonPayload, size_t /*len*/) {
#ifndef NATIVE_TEST
    // Emit a framed line that the gateway serial_json mode can parse.
    // Format: VGPAYLOAD:<json>\r\n
    Serial.print("VGPAYLOAD:");
    Serial.println(jsonPayload);
    Serial.flush();
#else
    printf("VGPAYLOAD:%s\n", jsonPayload);
#endif
    return true;
}
