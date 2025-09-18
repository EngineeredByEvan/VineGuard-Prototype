#include <Arduino.h>
#include <WiFi.h>
#include <esp_sleep.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/event_groups.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include "CommManager.h"
#include "NodeConfig.h"
#include "SensorInterfaces.h"
#include "StatusLed.h"
#include "TelemetryBuilder.h"
#include <ArduinoJson.h>

#ifdef __has_include
#  if __has_include("config.h")
#    include "config.h"
#  endif
#endif
#include "config_defaults.h"

#include <HTTPClient.h>
#include <HTTPUpdate.h>

#include <string>

#ifndef VERSION
#define VERSION "dev"
#endif

namespace {
constexpr uint8_t kSoilMoisturePin = 34;
constexpr uint8_t kSoilTempPin = 4;
constexpr uint8_t kBatteryPin = 35;
#ifndef STATUS_LED_PIN
constexpr uint8_t kStatusLedPin = 2;
#else
constexpr uint8_t kStatusLedPin = STATUS_LED_PIN;
#endif

constexpr uint16_t kSoilDryRef = 3200;
constexpr uint16_t kSoilWetRef = 1400;
constexpr uint16_t kAdcMax = 4095;
constexpr float kAdcReferenceVoltage = 3.3f;
constexpr float kBatteryR1 = 100000.0f;
constexpr float kBatteryR2 = 10000.0f;

AnalogSoilMoistureSensor soilMoistureSensor(kSoilMoisturePin, kSoilDryRef, kSoilWetRef);
SoilTemperatureSensor soilTemperatureSensor(kSoilTempPin);
AmbientClimateSensor ambientSensor;
LightSensor lightSensor;
BatteryMonitor batteryMonitor(kBatteryPin, kAdcMax, kAdcReferenceVoltage, kBatteryR1, kBatteryR2);

NodeConfigManager configManager;
NodeConfig currentConfig;
std::unique_ptr<ITelemetryPublisher> publisher;
StatusLed statusLed(kStatusLedPin);
QueueHandle_t telemetryQueue = nullptr;
EventGroupHandle_t systemEvents = nullptr;
TaskHandle_t sensingTaskHandle = nullptr;
TaskHandle_t uplinkTaskHandle = nullptr;
TaskHandle_t powerTaskHandle = nullptr;
SemaphoreHandle_t publisherMutex = nullptr;

constexpr EventBits_t EVENT_SAMPLE_READY = BIT0;
constexpr EventBits_t EVENT_UPLINK_COMPLETE = BIT1;

struct TelemetryMessage {
    SensorSnapshot snapshot;
    uint64_t timestampMs;
    bool success;
};

volatile bool configNeedsReinit = false;
volatile bool otaRequested = false;
String pendingOtaUrl;

TelemetryMessage latestMessage{};

void requestSample();
void sensingTask(void *param);
void uplinkTask(void *param);
void powerTask(void *param);
void handleCommand(const String &payload);
void performOtaUpdate(const String &url);

TelemetryMessage buildTelemetryMessage(const SensorSnapshot &snapshot) {
    TelemetryMessage msg{};
    msg.snapshot = snapshot;
    msg.timestampMs = static_cast<uint64_t>(esp_timer_get_time() / 1000ULL);
    msg.success = true;
    return msg;
}

void reconfigurePublisher() {
    if (!configNeedsReinit) {
        return;
    }
    if (publisherMutex) {
        xSemaphoreTake(publisherMutex, portMAX_DELAY);
    }
    publisher = createPublisher(currentConfig.useLoRa);
    if (publisher) {
        publisher->setCommandHandler(handleCommand);
        publisher->begin(currentConfig);
    }
    if (publisherMutex) {
        xSemaphoreGive(publisherMutex);
    }
    configNeedsReinit = false;
}

void performOtaUpdate(const String &url) {
    if (url.isEmpty()) {
        return;
    }
#ifdef LAB_MODE_WIFI
    Serial.print("[LAB_MODE][OTA] Requested update from ");
    Serial.println(url);
    return;
#else
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[OTA] WiFi not connected, aborting");
        return;
    }
    statusLed.setPattern(LedPattern::Ota);
    WiFiClientSecure client;
    client.setInsecure();
    Serial.print("[OTA] Fetching ");
    Serial.println(url);
    t_httpUpdate_return ret = httpUpdate.update(client, url);
    if (ret != HTTP_UPDATE_OK) {
        Serial.printf("[OTA] Update failed: %s\n", httpUpdate.getLastErrorString().c_str());
        statusLed.setPattern(LedPattern::Error);
    } else {
        Serial.println("[OTA] Update applied, rebooting");
    }
#endif
}

void handleCommand(const String &payload) {
    StaticJsonDocument<768> doc;
    const auto err = deserializeJson(doc, payload);
    if (err != DeserializationError::Ok) {
        Serial.printf("[CMD] Invalid JSON: %s\n", err.c_str());
        return;
    }
    const String cmd = doc["cmd"].as<String>();
    if (cmd.equalsIgnoreCase("set_config")) {
        if (!doc.containsKey("config")) {
            Serial.println("[CMD] Missing config payload");
            return;
        }
        String configJson;
        serializeJson(doc["config"], configJson);
        bool ota = false;
        if (configManager.updateFromJson(configJson, ota)) {
            currentConfig = configManager.getConfig();
            configNeedsReinit = true;
            Serial.println("[CMD] Configuration updated");
        }
        if (ota) {
            pendingOtaUrl = String(currentConfig.otaUrl);
            otaRequested = true;
        }
    } else if (cmd.equalsIgnoreCase("ota")) {
        const String url = doc["otaUrl"].as<String>();
        if (url.length() > 0) {
            strlcpy(currentConfig.otaUrl, url.c_str(), sizeof(currentConfig.otaUrl));
            configManager.setConfig(currentConfig);
            configManager.save();
            pendingOtaUrl = url;
            otaRequested = true;
            Serial.println("[CMD] OTA request stored");
        }
    } else if (doc.containsKey("otaUrl")) {
        const String url = doc["otaUrl"].as<String>();
        if (url.length() > 0) {
            strlcpy(currentConfig.otaUrl, url.c_str(), sizeof(currentConfig.otaUrl));
            configManager.setConfig(currentConfig);
            configManager.save();
            pendingOtaUrl = url;
            otaRequested = true;
            Serial.println("[CMD] OTA URL received");
        }
    } else {
        Serial.print("[CMD] Unknown command: ");
        Serial.println(cmd);
    }
}

void requestSample() {
    if (sensingTaskHandle) {
        xTaskNotifyGive(sensingTaskHandle);
    }
}

void sensingTask(void *param) {
    (void)param;
    SensorSnapshot snapshot{};
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        SoilMoistureData soilMoisture{};
        TemperatureData soilTemp{};
        AmbientClimateData ambient{};
        LightData light{};
        BatteryData battery{};

        bool success = true;
        success &= soilMoistureSensor.read(soilMoisture);
        success &= soilTemperatureSensor.read(soilTemp);
        success &= ambientSensor.read(ambient);
        success &= lightSensor.read(light);
        success &= batteryMonitor.read(battery);

        snapshot.soilMoisture = soilMoisture;
        snapshot.soilTemperature = soilTemp;
        snapshot.ambient = ambient;
        snapshot.light = light;
        snapshot.battery = battery;

        latestMessage = buildTelemetryMessage(snapshot);
        latestMessage.success = success;

        if (telemetryQueue) {
            xQueueOverwrite(telemetryQueue, &latestMessage);
        }
        xEventGroupSetBits(systemEvents, EVENT_SAMPLE_READY);
    }
}

void uplinkTask(void *param) {
    (void)param;
    for (;;) {
        if (publisherMutex) {
            if (xSemaphoreTake(publisherMutex, pdMS_TO_TICKS(200)) == pdPASS) {
                if (publisher) {
                    publisher->loop();
                }
                xSemaphoreGive(publisherMutex);
            }
        }
        EventBits_t bits = xEventGroupWaitBits(systemEvents, EVENT_SAMPLE_READY, pdTRUE, pdFALSE, pdMS_TO_TICKS(500));
        if ((bits & EVENT_SAMPLE_READY) == 0) {
            continue;
        }
        TelemetryMessage message{};
        if (telemetryQueue && xQueueReceive(telemetryQueue, &message, 0) != pdPASS) {
            continue;
        }

        TelemetryData data{
            .version = VERSION,
            .orgId = std::string(currentConfig.orgId),
            .siteId = std::string(currentConfig.siteId),
            .nodeId = std::string(currentConfig.nodeId),
            .timestampMs = message.timestampMs,
            .soilMoisture = message.snapshot.soilMoisture.normalized,
            .soilTemperatureC = message.snapshot.soilTemperature.temperatureC,
            .ambientTemperatureC = message.snapshot.ambient.temperatureC,
            .ambientHumidity = message.snapshot.ambient.humidity,
            .lightLux = message.snapshot.light.lux,
            .batteryVoltage = message.snapshot.battery.voltage,
        };

        std::string payload = buildTelemetryJson(data);
        bool published = false;
        if (publisherMutex) {
            xSemaphoreTake(publisherMutex, portMAX_DELAY);
            if (publisher) {
                published = publisher->publish(payload);
            }
            xSemaphoreGive(publisherMutex);
        }
        if (published) {
            Serial.print("[Uplink] Published telemetry: ");
            Serial.println(payload.c_str());
            statusLed.setPattern(LedPattern::Ok);
        } else {
            Serial.println("[Uplink] Publish failed");
            statusLed.setPattern(LedPattern::Error);
        }

        xEventGroupSetBits(systemEvents, EVENT_UPLINK_COMPLETE);
    }
}

void powerTask(void *param) {
    (void)param;
    requestSample();
    for (;;) {
        EventBits_t bits = xEventGroupWaitBits(systemEvents, EVENT_UPLINK_COMPLETE, pdTRUE, pdFALSE, portMAX_DELAY);
        if ((bits & EVENT_UPLINK_COMPLETE) == 0) {
            continue;
        }
        if (configNeedsReinit) {
            reconfigurePublisher();
        }
        if (otaRequested) {
            if (!currentConfig.useLoRa) {
                performOtaUpdate(pendingOtaUrl);
            } else {
                Serial.println("[Power] OTA requested but node is in LoRa mode; connect Wi-Fi to update");
            }
            otaRequested = false;
        }
#ifdef LAB_MODE
        const uint32_t delayMs = currentConfig.publishIntervalSeconds * 1000U;
        vTaskDelay(pdMS_TO_TICKS(delayMs));
        requestSample();
#else
        if (currentConfig.sleepStrategy == SleepStrategy::StayAwake) {
            const uint32_t delayMs = currentConfig.publishIntervalSeconds * 1000U;
            vTaskDelay(pdMS_TO_TICKS(delayMs));
            requestSample();
        } else {
            Serial.println("[Power] Entering deep sleep");
            statusLed.setPattern(LedPattern::Off);
            esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(currentConfig.publishIntervalSeconds) * 1000000ULL);
            vTaskDelay(pdMS_TO_TICKS(100));
            esp_deep_sleep_start();
        }
#endif
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println("VineGuard ESP32 Node starting");

    statusLed.begin();
    statusLed.setPattern(LedPattern::Ok);

    if (!configManager.begin()) {
        Serial.println("[Config] Failed to init NVS");
    }
    currentConfig = configManager.getConfig();
    Serial.print("[Config] Loaded publish interval: ");
    Serial.println(currentConfig.publishIntervalSeconds);

    if (!soilMoistureSensor.begin()) {
        Serial.println("[Sensor] Soil moisture init failed");
    }
    if (!soilTemperatureSensor.begin()) {
        Serial.println("[Sensor] Soil temperature init failed");
    }
    if (!ambientSensor.begin()) {
        Serial.println("[Sensor] Ambient sensor init failed");
    }
    if (!lightSensor.begin()) {
        Serial.println("[Sensor] Light sensor init failed");
    }
    if (!batteryMonitor.begin()) {
        Serial.println("[Sensor] Battery monitor init failed");
    }

    telemetryQueue = xQueueCreate(1, sizeof(TelemetryMessage));
    systemEvents = xEventGroupCreate();
    publisherMutex = xSemaphoreCreateMutex();

    publisher = createPublisher(currentConfig.useLoRa);
    if (publisher) {
        publisher->setCommandHandler(handleCommand);
        publisher->begin(currentConfig);
    }

    xTaskCreatePinnedToCore(sensingTask, "sensing", 4096, nullptr, 2, &sensingTaskHandle, 1);
    xTaskCreatePinnedToCore(uplinkTask, "uplink", 6144, nullptr, 1, &uplinkTaskHandle, 1);
    xTaskCreatePinnedToCore(powerTask, "power", 4096, nullptr, 1, &powerTaskHandle, 0);

    Serial.println("[Setup] Tasks started");
}

void loop() {
    statusLed.update();
    delay(50);
}
