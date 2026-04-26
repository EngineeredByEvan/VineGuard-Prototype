#include "SleepManager.h"

#include <Arduino.h>

void SleepManager::sleepSeconds(uint32_t seconds) {
#if ENABLE_DEEP_SLEEP
  esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(seconds) * 1000000ULL);
  esp_deep_sleep_start();
#else
  delay(seconds * 1000UL);
#endif
}
