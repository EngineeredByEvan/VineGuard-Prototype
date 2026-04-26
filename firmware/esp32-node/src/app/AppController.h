#pragma once

#include "comms/UplinkClient.h"
#include "config.h"
#include "sensors/SensorManager.h"
#include "storage/FailsafeQueue.h"
#include "storage/NvsConfigStore.h"

class AppController {
 public:
  AppController();
  void setup();
  void runCycle();

 private:
  RuntimeConfig cfg_;
  NvsConfigStore cfgStore_;
  SensorManager sensors_;
  FailsafeQueue queue_;
  UplinkClient* uplink_;
  uint32_t sequence_ = 0;
  uint32_t bootCount_ = 0;

  void initUplink();
};
