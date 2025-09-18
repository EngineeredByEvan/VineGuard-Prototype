#include "CommManager.h"

#ifdef __has_include
#  if __has_include("config.h")
#    include "config.h"
#  endif
#endif
#include "config_defaults.h"

#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <functional>

#include <LoRa.h>
#include <PubSubClient.h>

namespace {
WifiMqttPublisher *g_wifiPublisher = nullptr;
}

LoRaPublisher::LoRaPublisher() : initialized_(false) {}

bool LoRaPublisher::begin(const NodeConfig &config) {
    (void)config;
    SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
    if (!LoRa.begin(915E6)) {
        initialized_ = false;
        Serial.println("[LoRa] Failed to start radio");
        return false;
    }
    LoRa.enableCrc();
    initialized_ = true;
    Serial.println("[LoRa] Radio initialized");
    return true;
}

bool LoRaPublisher::publish(const std::string &payload) {
    if (!initialized_) {
        return false;
    }
    LoRa.beginPacket();
    LoRa.print(payload.c_str());
    LoRa.endPacket(true);
    return true;
}

void LoRaPublisher::loop() {
    if (!initialized_) {
        return;
    }
    int packetSize = LoRa.parsePacket();
    if (packetSize <= 0) {
        return;
    }
    String incoming;
    while (LoRa.available()) {
        incoming += static_cast<char>(LoRa.read());
    }
    if (handler_) {
        handler_(incoming);
    }
}

bool LoRaPublisher::isConnected() const { return initialized_; }

void LoRaPublisher::setCommandHandler(std::function<void(const String &)> handler) { handler_ = handler; }

WifiMqttPublisher::WifiMqttPublisher()
    : lastReconnectAttempt_(0), mqttConnected_(false) {
    g_wifiPublisher = this;
    wifiClient_ = std::unique_ptr<WiFiClientSecure>(new WiFiClientSecure());
    wifiClient_->setInsecure();
    mqttClient_ = std::unique_ptr<PubSubClient>(new PubSubClient(*wifiClient_));
}

bool WifiMqttPublisher::begin(const NodeConfig &config) {
    currentConfig_ = config;
    telemetryTopic_ = String("/") + config.orgId + "/" + config.siteId + "/" + config.nodeId + "/telemetry";
    commandTopic_ = String("/") + config.orgId + "/" + config.siteId + "/" + config.nodeId + "/cmd";
    lastReconnectAttempt_ = 0;

#ifdef LAB_MODE_WIFI
    Serial.println("[LAB_MODE] WiFi MQTT publisher stub active");
    mqttConnected_ = true;
    return true;
#else
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    mqttClient_->setServer(config.mqttHost, config.mqttPort);
    mqttClient_->setCallback([](char *topic, uint8_t *payload, unsigned int length) {
        if (g_wifiPublisher) {
            g_wifiPublisher->handleMqttMessage(topic, payload, length);
        }
    });
    ensureConnected();
    return true;
#endif
}

bool WifiMqttPublisher::publish(const std::string &payload) {
#ifdef LAB_MODE_WIFI
    Serial.print("[LAB_MODE][MQTT] ");
    Serial.print(telemetryTopic_);
    Serial.print(" <= ");
    Serial.println(payload.c_str());
    return true;
#else
    ensureConnected();
    if (!mqttClient_ || !mqttClient_->connected()) {
        return false;
    }
    return mqttClient_->publish(telemetryTopic_.c_str(), payload.c_str());
#endif
}

void WifiMqttPublisher::loop() {
#ifdef LAB_MODE_WIFI
    if (!handler_) {
        return;
    }
    while (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) {
            continue;
        }
        if (line.charAt(0) == '{') {
            handler_(line);
        }
    }
#else
    ensureConnected();
    if (mqttClient_) {
        mqttClient_->loop();
    }
#endif
}

bool WifiMqttPublisher::isConnected() const {
#ifdef LAB_MODE_WIFI
    return true;
#else
    return mqttConnected_ && mqttClient_ && mqttClient_->connected();
#endif
}

void WifiMqttPublisher::setCommandHandler(std::function<void(const String &)> handler) {
    handler_ = handler;
}

void WifiMqttPublisher::ensureConnected() {
#ifdef LAB_MODE_WIFI
    mqttConnected_ = true;
    return;
#else
    if (WiFi.status() != WL_CONNECTED) {
        if (millis() - lastReconnectAttempt_ > 5000) {
            lastReconnectAttempt_ = millis();
            Serial.println("[WiFi] Attempting reconnect");
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
        mqttConnected_ = false;
        return;
    }
    if (!mqttClient_) {
        return;
    }
    if (!mqttClient_->connected()) {
        if (millis() - lastReconnectAttempt_ > 2000) {
            lastReconnectAttempt_ = millis();
            Serial.println("[MQTT] Connecting...");
            if (mqttClient_->connect(currentConfig_.nodeId, currentConfig_.mqttUser, currentConfig_.mqttPassword)) {
                mqttClient_->subscribe(commandTopic_.c_str());
                mqttConnected_ = true;
                Serial.println("[MQTT] Connected");
            } else {
                mqttConnected_ = false;
            }
        }
    } else {
        mqttConnected_ = true;
    }
#endif
}

void WifiMqttPublisher::handleMqttMessage(char *topic, uint8_t *payload, unsigned int length) {
#ifndef LAB_MODE_WIFI
    if (!handler_) {
        return;
    }
    if (String(topic) != commandTopic_) {
        return;
    }
    String message;
    for (unsigned int i = 0; i < length; ++i) {
        message += static_cast<char>(payload[i]);
    }
    handler_(message);
#else
    (void)topic;
    (void)payload;
    (void)length;
#endif
}

std::unique_ptr<ITelemetryPublisher> createPublisher(bool useLoRa) {
    if (useLoRa) {
        return std::unique_ptr<ITelemetryPublisher>(new LoRaPublisher());
    }
    return std::unique_ptr<ITelemetryPublisher>(new WifiMqttPublisher());
}
