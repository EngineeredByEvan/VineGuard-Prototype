#include "SleepManager.h"

#ifndef NATIVE_TEST
  #include <Arduino.h>
  #include "esp_sleep.h"
#endif

static const char* TAG = "SLEEP";

// RTC memory survives deep sleep (zero-initialised on power-on reset)
#ifndef NATIVE_TEST
RTC_DATA_ATTR static uint32_t rtcSequence = 0;
RTC_DATA_ATTR static uint32_t rtcUptimeSec = 0;
#else
static uint32_t rtcSequence = 0;
static uint32_t rtcUptimeSec = 0;
#endif

void SleepManager::deepSleep(uint32_t durationSec) {
#if USE_DEEP_SLEEP && !defined(NATIVE_TEST)
    LOG_INFO(TAG, "Deep sleep for %us", durationSec);
    rtcUptimeSec += durationSec;
    uint64_t us = (uint64_t)durationSec * 1000000ULL;
    esp_sleep_enable_timer_wakeup(us);
    esp_deep_sleep_start();
    // Never reaches here
#else
    debugDelay(durationSec);
#endif
}

void SleepManager::debugDelay(uint32_t durationSec) {
#ifndef NATIVE_TEST
    LOG_DBG(TAG, "Delay %us (no deep sleep)", durationSec);
    uint32_t start = millis();
    while ((millis() - start) < durationSec * 1000UL) {
        delay(100);
        // Yield to allow watchdog feeding
    }
    rtcUptimeSec += durationSec;
#else
    rtcUptimeSec += durationSec;
#endif
}

uint32_t SleepManager::getUptimeSec() {
#ifndef NATIVE_TEST
    return rtcUptimeSec + millis() / 1000;
#else
    return rtcUptimeSec;
#endif
}

uint32_t SleepManager::getAndIncrementSequence() {
    return rtcSequence++;
}
