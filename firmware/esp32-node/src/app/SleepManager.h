#pragma once
#include <stdint.h>
#include "../../include/build_config.h"
#include "../util/Logger.h"

// Deep sleep management for power-constrained nodes.
// When USE_DEEP_SLEEP=1 the node sleeps between cycles using esp_deep_sleep.
// RTC memory preserves the sequence counter across wakes.

class SleepManager {
public:
    // Enter deep sleep for durationSec seconds.
    // Never returns; the next execution starts from setup() (cold restart
    // of application code, RTC memory preserved).
    static void deepSleep(uint32_t durationSec);

    // Non-blocking delay for USE_DEEP_SLEEP=0 debug mode.
    static void debugDelay(uint32_t durationSec);

    // Total uptime in seconds (accounts for deep sleep wakes via RTC).
    // Stored in RTC memory so it increments across wakes.
    static uint32_t getUptimeSec();

    // Sequence counter – increments each wake/transmit cycle.
    // Stored in RTC memory.
    static uint32_t getAndIncrementSequence();
};
