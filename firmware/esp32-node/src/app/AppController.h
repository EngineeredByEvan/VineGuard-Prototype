#pragma once
#include <Arduino.h>
#include "../../include/config.h"
#include "../../include/build_config.h"
#include "TelemetryBuilder.h"
#include "SleepManager.h"
#include "HealthStatus.h"
#include "../sensors/SensorManager.h"
#include "../comms/UplinkClient.h"
#include "../storage/FailsafeQueue.h"
#include "../storage/NvsConfigStore.h"
#include "../ota/OtaUpdater.h"
#include "../util/Logger.h"

// AppController owns all subsystems and orchestrates the sample-transmit cycle.
// Call setup() once from Arduino setup(), then call loop() from Arduino loop().

class AppController {
public:
    AppController();

    // Initialise all subsystems.
    void setup();

    // Execute one sample-transmit cycle.  In deep sleep mode this function
    // ends with a call to SleepManager::deepSleep() and never returns.
    // In polling mode it returns normally after a blocking delay.
    void loop();

private:
    DeviceConfig   _cfg;
    SensorReadings _readings;
    HealthStatus   _health;

    SensorManager  _sensors;
    FailsafeQueue  _queue;
    NvsConfigStore _nvs;
    OtaUpdater     _ota;

    UplinkClient*  _uplink = nullptr;

    char _jsonBuf[512];
    char _compactBuf[256];

    void runSampleCycle();
    void runTransmitCycle();
    void drainQueue();
    void buildPayload();
    bool chooseUplink();
    void logHealth() const;
};
