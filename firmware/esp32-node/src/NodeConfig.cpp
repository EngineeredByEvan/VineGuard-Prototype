#include "NodeConfig.h"

#ifdef __has_include
#  if __has_include("config.h")
#    include "config.h"
#  endif
#endif
#include "config_defaults.h"

#include <ArduinoJson.h>
#include <cstring>

namespace {
constexpr uint32_t kMagic = 0x56474E44;  // 'VGND'
constexpr uint32_t kConfigVersion = 1;
}

NodeConfig makeDefaultConfig() {
    NodeConfig cfg{};
    cfg.magic = kMagic;
    cfg.version = kConfigVersion;
    cfg.publishIntervalSeconds = 900;  // 15 minutes
    cfg.sleepStrategy = SleepStrategy::DeepSleep;
    cfg.useLoRa = true;
    strlcpy(cfg.mqttHost, LAB_MQTT_BROKER, sizeof(cfg.mqttHost));
    cfg.mqttPort = LAB_MQTT_PORT;
    strlcpy(cfg.mqttUser, LAB_MQTT_USER, sizeof(cfg.mqttUser));
    strlcpy(cfg.mqttPassword, LAB_MQTT_PASSWORD, sizeof(cfg.mqttPassword));
    strlcpy(cfg.orgId, "vineguard", sizeof(cfg.orgId));
    strlcpy(cfg.siteId, "lab", sizeof(cfg.siteId));
    strlcpy(cfg.nodeId, "esp32-node", sizeof(cfg.nodeId));
    cfg.otaUrl[0] = '\0';
    return cfg;
}

bool NodeConfigManager::begin() {
    if (!prefs_.begin("nodecfg", false)) {
        return false;
    }
    config_ = makeDefaultConfig();
    if (!load()) {
        config_ = makeDefaultConfig();
        return save();
    }
    return true;
}

NodeConfig NodeConfigManager::getConfig() const { return config_; }

void NodeConfigManager::setConfig(const NodeConfig &cfg) { config_ = cfg; }

bool NodeConfigManager::load() {
    if (!prefs_.isKey("config")) {
        config_ = makeDefaultConfig();
        return true;
    }
    NodeConfig cfg{};
    const size_t length = prefs_.getBytesLength("config");
    if (length != sizeof(NodeConfig)) {
        config_ = makeDefaultConfig();
        return false;
    }
    prefs_.getBytes("config", &cfg, sizeof(NodeConfig));
    if (cfg.magic != kMagic || cfg.version != kConfigVersion) {
        config_ = makeDefaultConfig();
        return false;
    }
    config_ = cfg;
    return true;
}

bool NodeConfigManager::save() {
    config_.magic = kMagic;
    config_.version = kConfigVersion;
    return prefs_.putBytes("config", &config_, sizeof(NodeConfig)) == sizeof(NodeConfig);
}

bool NodeConfigManager::updateFromJson(const String &json, bool &otaRequested) {
    otaRequested = false;
    StaticJsonDocument<512> doc;
    const auto err = deserializeJson(doc, json);
    if (err != DeserializationError::Ok) {
        return false;
    }

    bool dirty = false;
    if (doc.containsKey("publishIntervalSeconds")) {
        const uint32_t value = doc["publishIntervalSeconds"].as<uint32_t>();
        if (value != config_.publishIntervalSeconds && value >= 60) {
            config_.publishIntervalSeconds = value;
            dirty = true;
        }
    }
    if (doc.containsKey("sleepStrategy")) {
        const String strategy = doc["sleepStrategy"].as<String>();
        SleepStrategy desired = config_.sleepStrategy;
        if (strategy.equalsIgnoreCase("deepsleep")) {
            desired = SleepStrategy::DeepSleep;
        } else if (strategy.equalsIgnoreCase("stayawake")) {
            desired = SleepStrategy::StayAwake;
        }
        if (desired != config_.sleepStrategy) {
            config_.sleepStrategy = desired;
            dirty = true;
        }
    }
    if (doc.containsKey("useLoRa")) {
        const bool useLoRa = doc["useLoRa"].as<bool>();
        if (useLoRa != config_.useLoRa) {
            config_.useLoRa = useLoRa;
            dirty = true;
        }
    }
    if (doc.containsKey("mqtt")) {
        JsonObject mqtt = doc["mqtt"].as<JsonObject>();
        if (mqtt.containsKey("host")) {
            const String host = mqtt["host"].as<String>();
            if (host.length() > 0 && host != config_.mqttHost) {
                strlcpy(config_.mqttHost, host.c_str(), sizeof(config_.mqttHost));
                dirty = true;
            }
        }
        if (mqtt.containsKey("port")) {
            const uint16_t port = mqtt["port"].as<uint16_t>();
            if (port != 0 && port != config_.mqttPort) {
                config_.mqttPort = port;
                dirty = true;
            }
        }
        if (mqtt.containsKey("username")) {
            const String user = mqtt["username"].as<String>();
            if (user != config_.mqttUser) {
                strlcpy(config_.mqttUser, user.c_str(), sizeof(config_.mqttUser));
                dirty = true;
            }
        }
        if (mqtt.containsKey("password")) {
            const String password = mqtt["password"].as<String>();
            if (password != config_.mqttPassword) {
                strlcpy(config_.mqttPassword, password.c_str(), sizeof(config_.mqttPassword));
                dirty = true;
            }
        }
    }
    if (doc.containsKey("identity")) {
        JsonObject ident = doc["identity"].as<JsonObject>();
        if (ident.containsKey("org")) {
            const String org = ident["org"].as<String>();
            if (org.length() && org != config_.orgId) {
                strlcpy(config_.orgId, org.c_str(), sizeof(config_.orgId));
                dirty = true;
            }
        }
        if (ident.containsKey("site")) {
            const String site = ident["site"].as<String>();
            if (site.length() && site != config_.siteId) {
                strlcpy(config_.siteId, site.c_str(), sizeof(config_.siteId));
                dirty = true;
            }
        }
        if (ident.containsKey("node")) {
            const String node = ident["node"].as<String>();
            if (node.length() && node != config_.nodeId) {
                strlcpy(config_.nodeId, node.c_str(), sizeof(config_.nodeId));
                dirty = true;
            }
        }
    }
    if (doc.containsKey("otaUrl")) {
        const String url = doc["otaUrl"].as<String>();
        if (url.length() > 0 && url != config_.otaUrl) {
            strlcpy(config_.otaUrl, url.c_str(), sizeof(config_.otaUrl));
            otaRequested = true;
            dirty = true;
        }
    }
    if (dirty) {
        save();
    }
    return dirty;
}

String NodeConfigManager::toJson() const {
    StaticJsonDocument<512> doc;
    doc["publishIntervalSeconds"] = config_.publishIntervalSeconds;
    doc["sleepStrategy"] = config_.sleepStrategy == SleepStrategy::DeepSleep ? "deepSleep" : "stayAwake";
    doc["useLoRa"] = config_.useLoRa;

    JsonObject mqtt = doc.createNestedObject("mqtt");
    mqtt["host"] = config_.mqttHost;
    mqtt["port"] = config_.mqttPort;
    mqtt["username"] = config_.mqttUser;
    mqtt["password"] = config_.mqttPassword;

    JsonObject ident = doc.createNestedObject("identity");
    ident["org"] = config_.orgId;
    ident["site"] = config_.siteId;
    ident["node"] = config_.nodeId;

    if (strlen(config_.otaUrl) > 0) {
        doc["otaUrl"] = config_.otaUrl;
    }

    String json;
    serializeJson(doc, json);
    return json;
}
