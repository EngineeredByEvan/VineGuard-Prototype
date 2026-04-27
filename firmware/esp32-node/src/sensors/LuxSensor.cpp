#include "LuxSensor.h"

static const char* TAG = "LUX";

LuxSensor::LuxSensor(TwoWire& wire) : _wire(wire) {}

bool LuxSensor::init() {
#ifdef MOCK_SENSORS
    _present = true;
    LOG_INFO(TAG, "Mock mode");
    return true;
#endif

#ifdef NATIVE_TEST
    _present = true;
    return true;
#else
    if (!_veml.begin(&_wire)) {
        LOG_ERR(TAG, "VEML7700 not found – check wiring");
        _present = false;
        return false;
    }
    // Auto-gain; integration time 100 ms provides good dynamic range.
    _veml.setGain(VEML7700_GAIN_1);
    _veml.setIntegrationTime(VEML7700_IT_100MS);
    _present = true;
    LOG_INFO(TAG, "VEML7700 init OK");
    return true;
#endif
}

SensorResult LuxSensor::readLux() {
    SensorResult r;

#ifdef MOCK_SENSORS
    // Realistic daylight cycle: peaks ~35000 lux at noon, 0 at night
    static float lux = 12000.0f;
    static float dir = 150.0f;
    lux += dir;
    if (lux > 38000.0f || lux < 100.0f) dir = -dir;
    r.value  = lux;
    r.status = SensorStatus::MOCK;
    return r;
#endif

#ifdef NATIVE_TEST
    r.value  = 15000.0f;
    r.status = SensorStatus::MOCK;
    return r;
#else
    if (!_present) { r.status = SensorStatus::NOT_FOUND; return r; }

    float lux = _veml.readLux(VEML_LUX_AUTO);
    if (lux < 0.0f || lux > 200000.0f) {
        r.status = SensorStatus::READ_ERR;
        LOG_ERR(TAG, "Bad lux reading: %.1f", lux);
        return r;
    }
    r.value  = lux;
    r.status = SensorStatus::OK;
    LOG_DBG(TAG, "lux=%.1f", lux);
    return r;
#endif
}
