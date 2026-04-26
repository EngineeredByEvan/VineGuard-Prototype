#include <unity.h>

#include "../src/sensors/SoilMoistureSensor.h"

void test_map_to_percent_clamps() {
  TEST_ASSERT_EQUAL_FLOAT(0.0f, SoilMoistureSensor::mapToPercent(3500, 3000, 1500));
  TEST_ASSERT_EQUAL_FLOAT(100.0f, SoilMoistureSensor::mapToPercent(1000, 3000, 1500));
}

void test_map_to_percent_midpoint() {
  float v = SoilMoistureSensor::mapToPercent(2250, 3000, 1500);
  TEST_ASSERT_FLOAT_WITHIN(0.2f, 50.0f, v);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_map_to_percent_clamps);
  RUN_TEST(test_map_to_percent_midpoint);
  UNITY_END();
  return 0;
}
