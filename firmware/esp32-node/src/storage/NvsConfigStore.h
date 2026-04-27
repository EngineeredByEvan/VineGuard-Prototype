#pragma once
#include <Arduino.h>
#include "../../include/config.h"
#include "../util/Logger.h"

#ifndef NATIVE_TEST
  #include <Preferences.h>
#endif

// Persistent device identity and configuration stored in ESP32 NVS flash.
// Survives deep sleep and power cycles.
// Cleared only by explicit factory reset or flash erase.

class NvsConfigStore {
public:
    // Load config from NVS.  Missing keys use defaults from config.h.
    bool load(DeviceConfig& cfg);

    // Save config to NVS.
    bool save(const DeviceConfig& cfg);

    // Store a single calibration value by key.
    bool setFloat(const char* key, float value);
    float getFloat(const char* key, float defaultVal = 0.0f);

    // Store boot count and return incremented value.
    uint32_t incrementBootCount();
    uint32_t getBootCount();

    // Erase all VineGuard NVS keys (factory reset).
    void factoryReset();

private:
    static constexpr const char* NS = "vineguard";

#ifndef NATIVE_TEST
    Preferences _prefs;
#endif

    void open();
    void close();
};
