#include <unity.h>
#include <stdint.h>
#include <string.h>

// Standalone codec tests for the VGPP-1 binary payload format.
// These tests encode a known reading, then decode the binary and verify
// the round-trip accuracy matches the field resolutions.

// ─── Constants (mirror payload_schema.h without the MCU include chain) ────────
#define VGPP_PROTOCOL_V1 0xA1
#define FLAGS_SOIL_VALID      (1 << 0)
#define FLAGS_BME280_VALID    (1 << 2)
#define FLAGS_LUX_VALID       (1 << 3)
#define FLAGS_LEAF_WETNESS_VALID (1 << 4)
#define FLAGS_SOLAR_VALID     (1 << 5)

static uint16_t crc16(const uint8_t* d, int n) {
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < n; i++) {
        crc ^= (uint16_t)d[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : (crc << 1);
    }
    return crc;
}

// Encode a minimal frame with fixed values
static int encodeFrame(uint8_t* buf, int bufSize,
                       float soilPct, float atC, float rh, float hpa,
                       uint32_t lux, float battV, int battPct) {
    if (bufSize < 24) return -1;
    int idx = 0;
    uint16_t flags = FLAGS_SOIL_VALID | FLAGS_BME280_VALID | FLAGS_LUX_VALID;

    buf[idx++] = VGPP_PROTOCOL_V1;
    buf[idx++] = 0x01;  // seq lo
    buf[idx++] = 0x00;  // seq hi
    buf[idx++] = flags & 0xFF;
    buf[idx++] = (flags >> 8) & 0xFF;

    uint16_t soilX100 = (uint16_t)(soilPct * 100.0f);
    buf[idx++] = soilX100 & 0xFF;
    buf[idx++] = (soilX100 >> 8) & 0xFF;

    uint16_t stEnc = 0;  // soil temp not present
    buf[idx++] = stEnc & 0xFF;
    buf[idx++] = (stEnc >> 8) & 0xFF;

    uint16_t atEnc = (uint16_t)((atC + 40.0f) * 10.0f);
    buf[idx++] = atEnc & 0xFF;
    buf[idx++] = (atEnc >> 8) & 0xFF;

    uint16_t rhX100 = (uint16_t)(rh * 100.0f);
    buf[idx++] = rhX100 & 0xFF;
    buf[idx++] = (rhX100 >> 8) & 0xFF;

    uint16_t hpaEnc = (uint16_t)(hpa * 10.0f - 8500.0f);
    buf[idx++] = hpaEnc & 0xFF;
    buf[idx++] = (hpaEnc >> 8) & 0xFF;

    buf[idx++] = lux & 0xFF;
    buf[idx++] = (lux >> 8) & 0xFF;
    buf[idx++] = (lux >> 16) & 0xFF;

    buf[idx++] = (uint8_t)(battV * 10.0f);
    buf[idx++] = (uint8_t)battPct;

    uint16_t c = crc16(buf, idx);
    buf[idx++] = c & 0xFF;
    buf[idx++] = (c >> 8) & 0xFF;
    return idx;
}

static void decodeFrame(const uint8_t* buf, int len,
                        float* soilOut, float* atOut, float* rhOut,
                        float* hpaOut, uint32_t* luxOut,
                        float* battVOut, int* battPctOut) {
    // Verify CRC
    uint16_t storedCrc = (uint16_t)buf[len-2] | ((uint16_t)buf[len-1] << 8);
    uint16_t calcCrc   = crc16(buf, len - 2);
    (void)storedCrc; (void)calcCrc;  // tested separately

    uint16_t soilX100 = (uint16_t)buf[5] | ((uint16_t)buf[6] << 8);
    *soilOut = soilX100 / 100.0f;

    uint16_t atEnc = (uint16_t)buf[9] | ((uint16_t)buf[10] << 8);
    *atOut = atEnc / 10.0f - 40.0f;

    uint16_t rhX100 = (uint16_t)buf[11] | ((uint16_t)buf[12] << 8);
    *rhOut = rhX100 / 100.0f;

    uint16_t hpaEnc = (uint16_t)buf[13] | ((uint16_t)buf[14] << 8);
    *hpaOut = (hpaEnc + 8500.0f) / 10.0f;

    *luxOut = (uint32_t)buf[15] | ((uint32_t)buf[16] << 8) | ((uint32_t)buf[17] << 16);

    *battVOut  = buf[18] / 10.0f;
    *battPctOut = buf[19];
}

void test_frame_protocol_id() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 28.4f, 21.3f, 63.2f, 1007.2f, 24500, 11.5f, 65);
    TEST_ASSERT_GREATER_THAN(0, len);
    TEST_ASSERT_EQUAL_HEX8(VGPP_PROTOCOL_V1, buf[0]);
}

void test_frame_crc_valid() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 28.4f, 21.3f, 63.2f, 1007.2f, 24500, 11.5f, 65);
    uint16_t stored = (uint16_t)buf[len-2] | ((uint16_t)buf[len-1] << 8);
    uint16_t calc   = crc16(buf, len - 2);
    TEST_ASSERT_EQUAL_HEX16(calc, stored);
}

void test_frame_crc_detects_corruption() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 28.4f, 21.3f, 63.2f, 1007.2f, 24500, 11.5f, 65);
    buf[5] ^= 0xFF;  // corrupt soil moisture byte
    uint16_t stored = (uint16_t)buf[len-2] | ((uint16_t)buf[len-1] << 8);
    uint16_t calc   = crc16(buf, len - 2);
    TEST_ASSERT_NOT_EQUAL(calc, stored);
}

void test_soil_roundtrip_accuracy() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 28.4f, 20.0f, 60.0f, 1013.0f, 10000, 11.5f, 60);
    float soil; float at; float rh; float hpa; uint32_t lux; float bv; int bp;
    decodeFrame(buf, len, &soil, &at, &rh, &hpa, &lux, &bv, &bp);
    // Resolution 0.01%, expect ±0.01%
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 28.4f, soil);
}

void test_temperature_roundtrip_accuracy() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 30.0f, 21.3f, 65.0f, 1010.0f, 5000, 12.0f, 80);
    float soil; float at; float rh; float hpa; uint32_t lux; float bv; int bp;
    decodeFrame(buf, len, &soil, &at, &rh, &hpa, &lux, &bv, &bp);
    // Resolution 0.1°C
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 21.3f, at);
}

void test_lux_roundtrip_accuracy() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 30.0f, 20.0f, 60.0f, 1013.0f, 24500, 11.5f, 65);
    float soil; float at; float rh; float hpa; uint32_t lux; float bv; int bp;
    decodeFrame(buf, len, &soil, &at, &rh, &hpa, &lux, &bv, &bp);
    TEST_ASSERT_EQUAL_UINT32(24500, lux);
}

void test_battery_voltage_roundtrip() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 25.0f, 18.0f, 70.0f, 1005.0f, 8000, 11.5f, 65);
    float soil; float at; float rh; float hpa; uint32_t lux; float bv; int bp;
    decodeFrame(buf, len, &soil, &at, &rh, &hpa, &lux, &bv, &bp);
    // Resolution 0.1V
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 11.5f, bv);
}

void test_minimum_frame_length() {
    uint8_t buf[32];
    int len = encodeFrame(buf, sizeof(buf), 28.4f, 21.3f, 63.2f, 1007.2f, 24500, 11.5f, 65);
    // Minimum VGPP-1 frame without optional fields: 22 bytes
    TEST_ASSERT_EQUAL(22, len);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_frame_protocol_id);
    RUN_TEST(test_frame_crc_valid);
    RUN_TEST(test_frame_crc_detects_corruption);
    RUN_TEST(test_soil_roundtrip_accuracy);
    RUN_TEST(test_temperature_roundtrip_accuracy);
    RUN_TEST(test_lux_roundtrip_accuracy);
    RUN_TEST(test_battery_voltage_roundtrip);
    RUN_TEST(test_minimum_frame_length);
    return UNITY_END();
}
