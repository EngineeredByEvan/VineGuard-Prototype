#include <unity.h>
// Calibration and conversion math tests – no hardware needed.

// ─── Soil moisture ADC → percent ─────────────────────────────────────────────
static float adcToSoilPercent(int raw, int dryAdc, int wetAdc) {
    if (dryAdc == wetAdc) return 50.0f;
    float pct = (float)(dryAdc - raw) / (float)(dryAdc - wetAdc) * 100.0f;
    if (pct < 0.0f)   pct = 0.0f;
    if (pct > 100.0f) pct = 100.0f;
    return pct;
}

void test_soil_dry_reads_zero() {
    float pct = adcToSoilPercent(2800, 2800, 800);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 0.0f, pct);
}

void test_soil_wet_reads_hundred() {
    float pct = adcToSoilPercent(800, 2800, 800);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 100.0f, pct);
}

void test_soil_midpoint() {
    float pct = adcToSoilPercent(1800, 2800, 800);
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 50.0f, pct);
}

void test_soil_below_dry_clamped() {
    float pct = adcToSoilPercent(3200, 2800, 800);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, pct);
}

void test_soil_above_wet_clamped() {
    float pct = adcToSoilPercent(100, 2800, 800);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 100.0f, pct);
}

// ─── Battery voltage → percent ────────────────────────────────────────────────
static int battPct(float v, float vMin, float vMax) {
    if (v <= vMin) return 0;
    if (v >= vMax) return 100;
    return (int)((v - vMin) / (vMax - vMin) * 100.0f + 0.5f);
}

void test_batt_full_reads_100() {
    TEST_ASSERT_EQUAL(100, battPct(12.6f, 9.0f, 12.6f));
}

void test_batt_empty_reads_0() {
    TEST_ASSERT_EQUAL(0, battPct(9.0f, 9.0f, 12.6f));
}

void test_batt_below_empty_clamped() {
    TEST_ASSERT_EQUAL(0, battPct(7.0f, 9.0f, 12.6f));
}

void test_batt_above_full_clamped() {
    TEST_ASSERT_EQUAL(100, battPct(14.0f, 9.0f, 12.6f));
}

void test_batt_midpoint() {
    int pct = battPct(10.8f, 9.0f, 12.6f);
    TEST_ASSERT_INT_WITHIN(3, 50, pct);
}

// ─── ADC voltage conversion ───────────────────────────────────────────────────
static float adcToVoltage(int raw, float dividerRatio, float vrefMv = 3300.0f) {
    float adcV = (float)raw / 4095.0f * (vrefMv / 1000.0f);
    return adcV * dividerRatio;
}

void test_adc_voltage_full_scale() {
    float v = adcToVoltage(4095, 2.0f, 3300.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 3.3f * 2.0f, v);
}

void test_adc_voltage_zero() {
    float v = adcToVoltage(0, 2.0f, 3300.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, v);
}

void test_adc_voltage_12v_pack() {
    // 12V with 100k/11k divider (ratio 10.09): expect ~12V at ~2437 ADC counts
    // adcToVoltage(2437, 10.09f) ≈ 12.0 V
    float v = adcToVoltage(2437, 10.09f, 3300.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.2f, 12.0f, v);
}

// ─── Dew point calculation ─────────────────────────────────────────────────────
static float dewPoint(float tempC, float rhPct) {
    return tempC - ((100.0f - rhPct) / 5.0f);
}

void test_dew_point_typical() {
    // T=21.3, RH=63.2 → Td ≈ 13.9
    float td = dewPoint(21.3f, 63.2f);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 13.9f, td);
}

void test_dew_point_saturated() {
    // At 100% RH, dew point = air temperature
    float td = dewPoint(15.0f, 100.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 15.0f, td);
}

void test_dew_point_dry_air() {
    // At very low RH dew point is much lower than air temp
    float td = dewPoint(30.0f, 20.0f);
    TEST_ASSERT_LESS_THAN(10.0f, td);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_soil_dry_reads_zero);
    RUN_TEST(test_soil_wet_reads_hundred);
    RUN_TEST(test_soil_midpoint);
    RUN_TEST(test_soil_below_dry_clamped);
    RUN_TEST(test_soil_above_wet_clamped);
    RUN_TEST(test_batt_full_reads_100);
    RUN_TEST(test_batt_empty_reads_0);
    RUN_TEST(test_batt_below_empty_clamped);
    RUN_TEST(test_batt_above_full_clamped);
    RUN_TEST(test_batt_midpoint);
    RUN_TEST(test_adc_voltage_full_scale);
    RUN_TEST(test_adc_voltage_zero);
    RUN_TEST(test_adc_voltage_12v_pack);
    RUN_TEST(test_dew_point_typical);
    RUN_TEST(test_dew_point_saturated);
    RUN_TEST(test_dew_point_dry_air);
    return UNITY_END();
}
