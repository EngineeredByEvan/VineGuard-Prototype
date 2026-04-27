#include "Logger.h"
#include <stdarg.h>
#include <stdio.h>

static uint8_t s_level = DEBUG_LEVEL;

void Logger::init(uint32_t baud) {
#ifndef NATIVE_TEST
    Serial.begin(baud);
    unsigned long t0 = millis();
    while (!Serial && (millis() - t0) < 2000) {}
#endif
    s_level = DEBUG_LEVEL;
}

void Logger::setLevel(uint8_t level) {
    s_level = level;
}

void Logger::log(uint8_t level, const char* tag, const char* fmt, ...) {
    if (level > s_level) return;
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

#ifndef NATIVE_TEST
    uint32_t ms = millis();
    Serial.printf("[%6lu][%s] %s\r\n", ms, tag, buf);
#else
    printf("[%s] %s\n", tag, buf);
#endif
}
