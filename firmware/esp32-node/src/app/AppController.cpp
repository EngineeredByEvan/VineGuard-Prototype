#include "AppController.h"

// Conditionally include radio clients
#if defined(BUILD_MODE_LORA_P2P)
  #include "../comms/LoRaRadioClient.h"
  static LoRaRadioClient s_loraP2P;
#elif defined(BUILD_MODE_LORAWAN_OTAA)
  #include "../comms/LoRaWanClient.h"
  static LoRaWanClient s_loraWan;
#endif

#include "../comms/SerialDebugUplink.h"
static SerialDebugUplink s_serialUplink;

static const char* TAG = "APP";

AppController::AppController() {}

void AppController::setup() {
    Logger::init(115200);

    LOG_INFO(TAG, "=== VineGuard Node v%s ===", FW_VERSION_STR);
    LOG_INFO(TAG, "Build: %s",
#if defined(BUILD_MODE_DEBUG_SERIAL)
             "DEBUG_SERIAL"
#elif defined(BUILD_MODE_LORA_P2P)
             "LORA_P2P"
#elif defined(BUILD_MODE_LORAWAN_OTAA)
             "LORAWAN_OTAA"
#else
             "UNKNOWN"
#endif
    );

    // Load device config from NVS
    _nvs.load(_cfg);
    _health.bootCount = _nvs.incrementBootCount();

    LOG_INFO(TAG, "Device: %s  Boot#%u", _cfg.deviceId.c_str(), _health.bootCount);

    // Init persistent queue
    _queue.begin();

    // Init sensors
    _sensors.begin();

    // Choose and init uplink transport
    chooseUplink();
}

bool AppController::chooseUplink() {
#if defined(BUILD_MODE_DEBUG_SERIAL)
    _uplink = &s_serialUplink;
#elif defined(BUILD_MODE_LORA_P2P)
    if (s_loraP2P.begin()) {
        _uplink = &s_loraP2P;
        LOG_INFO(TAG, "Uplink: lora_p2p");
    } else {
        LOG_ERR(TAG, "LoRa P2P init failed, falling back to serial");
        s_serialUplink.begin();
        _uplink = &s_serialUplink;
    }
#elif defined(BUILD_MODE_LORAWAN_OTAA)
    if (s_loraWan.begin()) {
        _uplink = &s_loraWan;
        LOG_INFO(TAG, "Uplink: lorawan_otaa");
    } else {
        LOG_ERR(TAG, "LoRaWAN join failed, falling back to serial");
        s_serialUplink.begin();
        _uplink = &s_serialUplink;
    }
#else
    s_serialUplink.begin();
    _uplink = &s_serialUplink;
#endif
    _health.radioReady = (_uplink != nullptr && _uplink->isReady());
    return _health.radioReady;
}

void AppController::loop() {
    runSampleCycle();
    runTransmitCycle();

    // OTA check only when Wi-Fi is available (no-op for LoRa-only nodes)
    if (_ota.isEnabled()) _ota.checkAndApply();

    // Sleep or delay until next cycle
    uint32_t sleepSec = _cfg.sampleIntervalS;

    // Extend sleep on low battery to preserve power
    if (_health.criticalBattery) {
        sleepSec = min(sleepSec * 4, (uint32_t)3600);
        LOG_ERR(TAG, "Critical battery – extended sleep %us", sleepSec);
    } else if (_health.lowBattery) {
        sleepSec = sleepSec * 2;
        LOG_INFO(TAG, "Low battery – extended sleep %us", sleepSec);
    }

    SleepManager::deepSleep(sleepSec);
    // In polling mode deepSleep() returns; in deep sleep mode execution
    // restarts from setup() on next wake.
}

void AppController::runSampleCycle() {
    _health.sequence  = SleepManager::getAndIncrementSequence();
    _health.uptimeSec = SleepManager::getUptimeSec();

    LOG_INFO(TAG, "--- Sample cycle seq=%u ---", _health.sequence);
    _sensors.sample(_readings);

    _health.soilSensorOk   = _readings.soilOk;
    _health.bme280Ok       = _readings.bme280Ok;
    _health.luxSensorOk    = _readings.luxOk;
    _health.leafWetnessOk  = _readings.leafWetnessOk;
    _health.batteryOk      = _readings.batteryOk;
    _health.lowBattery     = _readings.batteryVoltage > 0.0f &&
                             _readings.batteryVoltage < BATTERY_LOW_THRESHOLD_V;
    _health.criticalBattery = _readings.batteryVoltage > 0.0f &&
                              _readings.batteryVoltage < BATTERY_CRITICAL_THRESHOLD_V;
    _health.failsafeQueueDepth = _queue.depth();

    logHealth();
}

void AppController::runTransmitCycle() {
    if (_health.criticalBattery) {
        LOG_ERR(TAG, "Skipping transmit – critical battery");
        return;
    }

    buildPayload();

    // First drain any backlogged payloads
    drainQueue();

    // Now transmit current payload
    bool sent = false;
    if (_uplink && _uplink->isReady()) {
#if defined(BUILD_MODE_LORA_P2P)
        sent = _uplink->send(_compactBuf, strlen(_compactBuf));
#else
        sent = _uplink->send(_jsonBuf, strlen(_jsonBuf));
#endif
    }

    if (!sent) {
        LOG_ERR(TAG, "Transmit failed, queuing payload");
        _queue.push(_jsonBuf);
        _health.failsafeQueueDepth = _queue.depth();
    }
}

void AppController::drainQueue() {
    if (_queue.isEmpty()) return;

    LOG_INFO(TAG, "Draining queue depth=%d", _queue.depth());
    String cached;
    int drained = 0;
    while (!_queue.isEmpty() && drained < 5) {  // drain max 5 per cycle
        if (!_queue.pop(cached)) break;
        if (_uplink && _uplink->isReady()) {
            if (_uplink->send(cached.c_str(), cached.length())) {
                drained++;
            } else {
                // Re-push and stop draining – channel still down
                _queue.push(cached.c_str());
                break;
            }
        } else {
            _queue.push(cached.c_str());
            break;
        }
    }
    if (drained > 0) LOG_INFO(TAG, "Drained %d cached payloads", drained);
}

void AppController::buildPayload() {
    TelemetryBuilder::buildV1Json(_cfg, _readings, _health, _jsonBuf, sizeof(_jsonBuf));
    TelemetryBuilder::buildCompactJson(_cfg, _readings, _health, _compactBuf, sizeof(_compactBuf));
    LOG_DBG(TAG, "V1 JSON: %s", _jsonBuf);
    LOG_DBG(TAG, "Compact: %s", _compactBuf);
}

void AppController::logHealth() const {
    LOG_INFO(TAG, "Health: soil=%d bme=%d lux=%d leaf=%d batt=%.2fV(%d%%) lowBatt=%d queue=%d",
             _health.soilSensorOk, _health.bme280Ok, _health.luxSensorOk,
             _health.leafWetnessOk, _readings.batteryVoltage, _readings.batteryPercent,
             _health.lowBattery, _health.failsafeQueueDepth);
}
