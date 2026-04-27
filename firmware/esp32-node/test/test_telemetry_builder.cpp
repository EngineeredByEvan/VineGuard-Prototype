#include <unity.h>
#include <ArduinoJson.h>
#include "../src/app/TelemetryBuilder.h"

// Test helpers
static DeviceConfig makeCfg() {
    DeviceConfig c;
    c.deviceId  = "vg-node-001";
    c.nodeType  = "basic";
    c.vineyardId = "vy-001";
    c.blockId    = "blk-cab";
    c.firmwareVersion = "0.1.0";
    c.sampleIntervalS   = 900;
    c.transmitIntervalS = 900;
    return c;
}

static SensorReadings makeHealthyReadings() {
    SensorReadings r;
    r.soilMoisturePercent = 28.4f;
    r.soilMoistureRaw     = 1832;
    r.soilVoltage         = 1.42f;
    r.soilOk              = true;
    r.ambientTempC        = 21.3f;
    r.ambientHumidityPct  = 63.2f;
    r.pressureHpa         = 1007.2f;
    r.dewPointC           = 13.9f;
    r.bme280Ok            = true;
    r.lightLux            = 24500.0f;
    r.luxOk               = true;
    r.batteryVoltage      = 11.5f;
    r.batteryPercent      = 65;
    r.batteryOk           = true;
    r.leafWetnessPercent  = -1.0f;
    r.leafWetnessOk       = false;
    return r;
}

static HealthStatus makeHealth() {
    HealthStatus h;
    h.soilSensorOk  = true;
    h.bme280Ok      = true;
    h.luxSensorOk   = true;
    h.batteryOk     = true;
    h.radioReady    = true;
    h.bootCount     = 3;
    h.sequence      = 42;
    h.uptimeSec     = 12600;
    return h;
}

void test_v1_json_required_fields() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    char buf[512];
    size_t len = TelemetryBuilder::buildV1Json(cfg, r, h, buf, sizeof(buf));

    TEST_ASSERT_GREATER_THAN(10, len);

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, buf);
    TEST_ASSERT_EQUAL(DeserializationError::Ok, err.code());

    TEST_ASSERT_EQUAL_STRING("1.0", doc["schema_version"]);
    TEST_ASSERT_EQUAL_STRING("vg-node-001", doc["device_id"]);
    TEST_ASSERT_EQUAL_STRING("basic", doc["tier"]);
    TEST_ASSERT_FALSE(doc["sensors"].isNull());
    TEST_ASSERT_FALSE(doc["meta"].isNull());
}

void test_v1_json_sensor_values() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    char buf[512];
    TelemetryBuilder::buildV1Json(cfg, r, h, buf, sizeof(buf));

    StaticJsonDocument<512> doc;
    deserializeJson(doc, buf);

    JsonObject sensors = doc["sensors"];
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 28.4f, sensors["soil_moisture_pct"].as<float>());
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 21.3f, sensors["ambient_temp_c"].as<float>());
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 63.2f, sensors["ambient_humidity_pct"].as<float>());
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 1007.2f, sensors["pressure_hpa"].as<float>());
    TEST_ASSERT_EQUAL(24500, sensors["light_lux"].as<int>());
    TEST_ASSERT_TRUE(sensors["leaf_wetness_pct"].isNull());
}

void test_v1_json_meta_fields() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    char buf[512];
    TelemetryBuilder::buildV1Json(cfg, r, h, buf, sizeof(buf));

    StaticJsonDocument<512> doc;
    deserializeJson(doc, buf);

    JsonObject meta = doc["meta"];
    TEST_ASSERT_FLOAT_WITHIN(0.05f, 11.5f, meta["battery_voltage"].as<float>());
    TEST_ASSERT_EQUAL(65, meta["battery_pct"].as<int>());
    TEST_ASSERT_TRUE(meta["sensor_ok"].as<bool>());
}

void test_v1_json_missing_bme280() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    r.bme280Ok         = false;
    r.ambientTempC     = -999.0f;
    r.ambientHumidityPct = -1.0f;
    r.pressureHpa      = -1.0f;
    HealthStatus h     = makeHealth();
    h.bme280Ok         = false;

    char buf[512];
    TelemetryBuilder::buildV1Json(cfg, r, h, buf, sizeof(buf));

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, buf);
    TEST_ASSERT_EQUAL(DeserializationError::Ok, err.code());

    JsonObject sensors = doc["sensors"];
    TEST_ASSERT_TRUE(sensors["ambient_temp_c"].isNull());
    TEST_ASSERT_TRUE(sensors["ambient_humidity_pct"].isNull());
    TEST_ASSERT_TRUE(sensors["pressure_hpa"].isNull());
    // Soil and lux should still be present
    TEST_ASSERT_FALSE(sensors["soil_moisture_pct"].isNull());
}

void test_compact_json_fits_lora() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    char buf[256];
    size_t len = TelemetryBuilder::buildCompactJson(cfg, r, h, buf, sizeof(buf));

    // Must fit within LoRa payload limit (222 bytes)
    TEST_ASSERT_LESS_THAN(222, len);
    TEST_ASSERT_GREATER_THAN(10, len);
}

void test_compact_json_has_required_keys() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    char buf[256];
    TelemetryBuilder::buildCompactJson(cfg, r, h, buf, sizeof(buf));

    StaticJsonDocument<384> doc;
    DeserializationError err = deserializeJson(doc, buf);
    TEST_ASSERT_EQUAL(DeserializationError::Ok, err.code());

    TEST_ASSERT_EQUAL(1, doc["v"].as<int>());
    TEST_ASSERT_EQUAL_STRING("vg-node-001", doc["id"]);
    TEST_ASSERT_EQUAL(42, doc["seq"].as<int>());
    TEST_ASSERT_FALSE(doc["sm"].isNull());
    TEST_ASSERT_FALSE(doc["at"].isNull());
    TEST_ASSERT_FALSE(doc["bv"].isNull());
}

void test_payload_buf_not_overflowed() {
    DeviceConfig   cfg = makeCfg();
    SensorReadings r   = makeHealthyReadings();
    HealthStatus   h   = makeHealth();

    // Deliberately small buffer
    char smallBuf[50];
    size_t len = TelemetryBuilder::buildV1Json(cfg, r, h, smallBuf, sizeof(smallBuf));
    // Should truncate gracefully (ArduinoJson returns 0 on buffer too small)
    TEST_ASSERT_LESS_THAN(50, len + 1);  // within buffer
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_v1_json_required_fields);
    RUN_TEST(test_v1_json_sensor_values);
    RUN_TEST(test_v1_json_meta_fields);
    RUN_TEST(test_v1_json_missing_bme280);
    RUN_TEST(test_compact_json_fits_lora);
    RUN_TEST(test_compact_json_has_required_keys);
    RUN_TEST(test_payload_buf_not_overflowed);
    return UNITY_END();
}
