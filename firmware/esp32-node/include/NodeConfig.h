#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include <functional>

enum class SleepStrategy : uint8_t {
    DeepSleep = 0,
    StayAwake = 1,
};

struct NodeConfig {
    uint32_t magic;
    uint32_t version;
    uint32_t publishIntervalSeconds;
    SleepStrategy sleepStrategy;
    bool useLoRa;
    char mqttHost[64];
    uint16_t mqttPort;
    char mqttUser[32];
    char mqttPassword[64];
    char orgId[32];
    char siteId[32];
    char nodeId[32];
    char otaUrl[128];
};

class NodeConfigManager {
   public:
    bool begin();
    NodeConfig getConfig() const;
    void setConfig(const NodeConfig &cfg);
    bool load();
    bool save();
    bool updateFromJson(const String &json, bool &otaRequested);
    String toJson() const;

   private:
    Preferences prefs_;
    NodeConfig config_{};
};

NodeConfig makeDefaultConfig();
