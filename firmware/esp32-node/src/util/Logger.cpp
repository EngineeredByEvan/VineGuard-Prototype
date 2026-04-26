#include "Logger.h"

namespace vg {
void logInfo(const String& msg) { Serial.println("[INFO] " + msg); }
void logWarn(const String& msg) { Serial.println("[WARN] " + msg); }
}
