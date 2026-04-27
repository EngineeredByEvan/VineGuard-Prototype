#include "NvsConfigStore.h"

static const char* TAG = "NVS";

void NvsConfigStore::open() {
#ifndef NATIVE_TEST
    _prefs.begin(NS, false);
#endif
}

void NvsConfigStore::close() {
#ifndef NATIVE_TEST
    _prefs.end();
#endif
}

bool NvsConfigStore::load(DeviceConfig& cfg) {
#ifdef NATIVE_TEST
    return true;
#else
    open();
    cfg.deviceId          = _prefs.getString("device_id",    DEFAULT_DEVICE_ID);
    cfg.nodeSerial        = _prefs.getString("node_serial",  DEFAULT_NODE_SERIAL);
    cfg.vineyardId        = _prefs.getString("vineyard_id",  DEFAULT_VINEYARD_ID);
    cfg.blockId           = _prefs.getString("block_id",     DEFAULT_BLOCK_ID);
    cfg.nodeType          = _prefs.getString("node_type",    DEFAULT_NODE_TYPE);
    cfg.firmwareVersion   = FW_VERSION_STR;
    cfg.sampleIntervalS   = _prefs.getUInt("sample_s",   SAMPLE_INTERVAL_S);
    cfg.transmitIntervalS = _prefs.getUInt("transmit_s", TRANSMIT_INTERVAL_S);
    close();
    LOG_INFO(TAG, "Loaded id=%s serial=%s vy=%s blk=%s type=%s",
             cfg.deviceId.c_str(), cfg.nodeSerial.c_str(),
             cfg.vineyardId.c_str(), cfg.blockId.c_str(), cfg.nodeType.c_str());
    return true;
#endif
}

bool NvsConfigStore::save(const DeviceConfig& cfg) {
#ifdef NATIVE_TEST
    return true;
#else
    open();
    _prefs.putString("device_id",    cfg.deviceId);
    _prefs.putString("node_serial",  cfg.nodeSerial);
    _prefs.putString("vineyard_id",  cfg.vineyardId);
    _prefs.putString("block_id",     cfg.blockId);
    _prefs.putString("node_type",    cfg.nodeType);
    _prefs.putUInt  ("sample_s",     cfg.sampleIntervalS);
    _prefs.putUInt  ("transmit_s",   cfg.transmitIntervalS);
    close();
    LOG_INFO(TAG, "Saved config for %s", cfg.deviceId.c_str());
    return true;
#endif
}

bool NvsConfigStore::setFloat(const char* key, float value) {
#ifdef NATIVE_TEST
    return true;
#else
    open();
    _prefs.putFloat(key, value);
    close();
    return true;
#endif
}

float NvsConfigStore::getFloat(const char* key, float defaultVal) {
#ifdef NATIVE_TEST
    return defaultVal;
#else
    open();
    float v = _prefs.getFloat(key, defaultVal);
    close();
    return v;
#endif
}

uint32_t NvsConfigStore::incrementBootCount() {
#ifdef NATIVE_TEST
    return 1;
#else
    open();
    uint32_t count = _prefs.getUInt("boot_count", 0) + 1;
    _prefs.putUInt("boot_count", count);
    close();
    return count;
#endif
}

uint32_t NvsConfigStore::getBootCount() {
#ifdef NATIVE_TEST
    return 0;
#else
    open();
    uint32_t count = _prefs.getUInt("boot_count", 0);
    close();
    return count;
#endif
}

void NvsConfigStore::factoryReset() {
#ifndef NATIVE_TEST
    _prefs.begin(NS, false);
    _prefs.clear();
    _prefs.end();
    LOG_INFO(TAG, "Factory reset: all NVS keys erased");
#endif
}
