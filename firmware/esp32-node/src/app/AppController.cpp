#include "AppController.h"

#include "app/HealthStatus.h"
#include "app/SleepManager.h"
#include "app/TelemetryBuilder.h"
#include "comms/LoRaRadioClient.h"
#include "comms/LoRaWanClient.h"
#include "comms/SerialDebugUplink.h"
#include "ota/OtaUpdater.h"
#include "pins.h"
#include "util/Logger.h"

namespace {
SerialDebugUplink gSerial;
LoRaRadioClient gP2P;
LoRaWanClient gLw;
}

AppController::AppController() : sensors_(cfg_), uplink_(&gSerial) {}

void AppController::initUplink() {
#if VINEGUARD_RADIO_MODE == MODE_LORA_P2P
  uplink_ = &gP2P;
#elif VINEGUARD_RADIO_MODE == MODE_LORAWAN_OTAA
  uplink_ = &gLw;
#else
  uplink_ = &gSerial;
#endif
  uplink_->begin();
}

void AppController::setup() {
  pinMode(PIN_SENSOR_RAIL_EN, OUTPUT);
  digitalWrite(PIN_SENSOR_RAIL_EN, HIGH);
  cfgStore_.load(cfg_);
  sensors_.begin();
  initUplink();
  bootCount_++;
}

void AppController::runCycle() {
  digitalWrite(PIN_SENSOR_RAIL_EN, HIGH);
  delay(300);

  SensorBundle sensorData = sensors_.sample();
  HealthStatus h;
  h.soilSensorOk = sensorData.soil.ok;
  h.bme280Ok = sensorData.ambient.ok;
  h.luxSensorOk = sensorData.lux.ok;
  h.leafWetnessOk = sensorData.leaf.ok || !ENABLE_LEAF_WETNESS;
  h.batteryOk = sensorData.battery.ok;
  h.lowBattery = sensorData.battery.lowBattery;
  h.failsafeQueueDepth = static_cast<int>(queue_.size());

  sequence_++;
  String payload = TelemetryBuilder::buildEnhancedJson(cfg_, sensorData, h, sequence_, bootCount_, millis() / 1000, uplink_->modeName());

  bool sent = uplink_->send(payload);
  if (!sent) {
    queue_.push(payload);
    vg::logWarn("uplink send failed, queued payload");
  } else {
    String queued;
    while (queue_.pop(queued)) {
      if (!uplink_->send(queued)) {
        queue_.push(queued);
        break;
      }
    }
  }

  // Legacy compatibility log for direct serial inspection.
  Serial.println("[LEGACY]" + TelemetryBuilder::buildLegacyFlatJson(cfg_, sensorData));
  OtaUpdater::check();

  digitalWrite(PIN_SENSOR_RAIL_EN, LOW);
  uint32_t sleepSec = cfg_.sampleIntervalSec;
  if (sensorData.battery.lowBattery) sleepSec *= 2;
  if (sensorData.battery.batteryVoltage < 3.35f) sleepSec *= 4;
  SleepManager::sleepSeconds(sleepSec);
}
