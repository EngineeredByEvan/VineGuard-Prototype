#include <unity.h>

#include "../src/util/Crc.h"

void test_crc_nonzero() {
  const uint8_t payload[] = {0x01, 0x02, 0x03};
  TEST_ASSERT_NOT_EQUAL(0, crc16_ccitt(payload, sizeof(payload)));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_crc_nonzero);
  UNITY_END();
  return 0;
}
