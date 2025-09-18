#pragma once

#include <Arduino.h>

#include <functional>
#include <memory>
#include <string>

#include "NodeConfig.h"

class WiFiClientSecure;
class PubSubClient;

class ITelemetryPublisher {
   public:
    virtual ~ITelemetryPublisher() = default;
    virtual bool begin(const NodeConfig &config) = 0;
    virtual bool publish(const std::string &payload) = 0;
    virtual void loop() = 0;
    virtual bool isConnected() const = 0;
    virtual void setCommandHandler(std::function<void(const String &)> handler) = 0;
};

class LoRaPublisher : public ITelemetryPublisher {
   public:
    LoRaPublisher();
    bool begin(const NodeConfig &config) override;
    bool publish(const std::string &payload) override;
    void loop() override;
    bool isConnected() const override;
    void setCommandHandler(std::function<void(const String &)> handler) override;

   private:
    std::function<void(const String &)> handler_;
    bool initialized_;
};

class WifiMqttPublisher : public ITelemetryPublisher {
   public:
    WifiMqttPublisher();
    bool begin(const NodeConfig &config) override;
    bool publish(const std::string &payload) override;
    void loop() override;
    bool isConnected() const override;
    void setCommandHandler(std::function<void(const String &)> handler) override;

   private:
    void ensureConnected();
    void handleMqttMessage(char *topic, uint8_t *payload, unsigned int length);

    NodeConfig currentConfig_{};
    std::function<void(const String &)> handler_;
    String telemetryTopic_;
    String commandTopic_;
    uint32_t lastReconnectAttempt_;
    bool mqttConnected_;
    std::unique_ptr<class WiFiClientSecure> wifiClient_;
    std::unique_ptr<class PubSubClient> mqttClient_;
};

std::unique_ptr<ITelemetryPublisher> createPublisher(bool useLoRa);
