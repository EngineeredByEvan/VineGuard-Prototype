#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

static DeviceConfig deviceConfig{
    .deviceId = "vineguard-node-001",
    .loraAppKey = "CHANGEME",
    .mqttBroker = "mqtts://gateway.local",
    .mqttPort = 8883,
    .mqttTopic = "vineguard/telemetry",
    .otaUrl = "https://ota.vineguard.local/firmware.bin"
};

static TaskHandle_t telemetryTaskHandle = nullptr;
static TaskHandle_t otaTaskHandle = nullptr;

SensorReadings readSensors() {
    // TODO: replace with real sensor drivers
    SensorReadings readings;
    readings.soilMoisture = random(300, 800) / 10.0f;
    readings.soilTemperatureC = random(150, 350) / 10.0f;
    readings.ambientTemperatureC = random(150, 350) / 10.0f;
    readings.ambientHumidity = random(400, 900) / 10.0f;
    readings.lightLux = random(0, 1000);
    readings.batteryVoltage = random(330, 420) / 100.0f;
    return readings;
}

void configurePowerManagement() {
    esp_sleep_enable_timer_wakeup(15 * 60 * 1000000ULL);
}

void connectLoRa() {
    // TODO: configure LMIC or RadioLib driver with proper keys
    Serial.println("[LoRa] connecting...");
}

void publishReadings(const SensorReadings &readings) {
    StaticJsonDocument<256> payload;
    payload["deviceId"] = deviceConfig.deviceId;
    payload["soilMoisture"] = readings.soilMoisture;
    payload["soilTempC"] = readings.soilTemperatureC;
    payload["ambientTempC"] = readings.ambientTemperatureC;
    payload["ambientHumidity"] = readings.ambientHumidity;
    payload["lightLux"] = readings.lightLux;
    payload["batteryVoltage"] = readings.batteryVoltage;
    payload["timestamp"] = (uint32_t) (millis() / 1000);

    String serialized;
    serializeJson(payload, serialized);

    Serial.printf("[Telemetry] %s\n", serialized.c_str());
    // TODO: send via LoRa uplink to gateway
}

void checkForOtaUpdates() {
    Serial.println("[OTA] checking for updates...");
    // TODO: implement secure OTA check
}

void telemetryTask(void *params) {
    for (;;) {
        SensorReadings readings = readSensors();
        publishReadings(readings);
        vTaskDelay(pdMS_TO_TICKS(30 * 1000));
    }
}

void otaTask(void *params) {
    for (;;) {
        checkForOtaUpdates();
        vTaskDelay(pdMS_TO_TICKS(15 * 60 * 1000));
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    configurePowerManagement();
    connectLoRa();

    xTaskCreatePinnedToCore(telemetryTask, "telemetry", 4096, nullptr, 1, &telemetryTaskHandle, 1);
    xTaskCreatePinnedToCore(otaTask, "ota", 4096, nullptr, 1, &otaTaskHandle, 0);
}

void loop() {
    // Sleep to conserve power
    vTaskDelay(pdMS_TO_TICKS(1000));
}
