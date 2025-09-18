#pragma once

#include <Arduino.h>

struct SensorReadings {
    float soilMoisture;
    float soilTemperatureC;
    float ambientTemperatureC;
    float ambientHumidity;
    float lightLux;
    float batteryVoltage;
};

struct DeviceConfig {
    String deviceId;
    String loraAppKey;
    String mqttBroker;
    uint16_t mqttPort;
    String mqttTopic;
    String otaUrl;
};

SensorReadings readSensors();
void configurePowerManagement();
void connectLoRa();
void publishReadings(const SensorReadings &readings);
void checkForOtaUpdates();
