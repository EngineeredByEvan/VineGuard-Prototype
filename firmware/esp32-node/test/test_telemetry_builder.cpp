#include <unity.h>

#include "../src/app/TelemetryBuilder.h"

void test_legacy_payload_contains_device() {
  RuntimeConfig cfg;
  cfg.identity.deviceId = "vg-node-test";
  SensorBundle s;
  s.soil.moisturePercent = 22.1f;
  s.battery.batteryVoltage = 3.9f;
  String payload = TelemetryBuilder::buildLegacyFlatJson(cfg, s);
  TEST_ASSERT_TRUE(payload.indexOf("vg-node-test") >= 0);
  TEST_ASSERT_TRUE(payload.indexOf("soilMoisture") >= 0);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_legacy_payload_contains_device);
  UNITY_END();
  return 0;
}
