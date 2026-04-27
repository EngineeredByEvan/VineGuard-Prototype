#pragma once
#include <Arduino.h>
#include "../../include/build_config.h"

// Structured serial logger.
// Levels: 0=silent, 1=error+info, 2=verbose/debug.
// In release builds (DEBUG_LEVEL=0) all macros expand to nothing.

#define LOG_TAG_MAX 16

namespace Logger {
    void init(uint32_t baud = 115200);
    void setLevel(uint8_t level);
    void log(uint8_t level, const char* tag, const char* fmt, ...);
}

#if DEBUG_LEVEL >= 1
  #define LOG_INFO(tag, fmt, ...) Logger::log(1, tag, fmt, ##__VA_ARGS__)
  #define LOG_ERR(tag, fmt, ...)  Logger::log(1, tag, "[ERR] " fmt, ##__VA_ARGS__)
#else
  #define LOG_INFO(tag, fmt, ...) ((void)0)
  #define LOG_ERR(tag, fmt, ...)  ((void)0)
#endif

#if DEBUG_LEVEL >= 2
  #define LOG_DBG(tag, fmt, ...) Logger::log(2, tag, fmt, ##__VA_ARGS__)
#else
  #define LOG_DBG(tag, fmt, ...) ((void)0)
#endif
