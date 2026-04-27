#include "SoilMoistureSensor.h"

static const char* TAG = "SOIL";

SoilMoistureSensor::SoilMoistureSensor(uint8_t pin, int dryAdc, int wetAdc)
    : _pin(pin), _dryAdc(dryAdc), _wetAdc(wetAdc) {}

void SoilMoistureSensor::init() {
#ifndef NATIVE_TEST
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);  // 0–3.3 V range
    pinMode(_pin, INPUT);
#endif

#ifdef MOCK_SENSORS
    _present = true;
    LOG_INFO(TAG, "Mock mode");
    return;
#endif

    // A capacitive sensor always reads something; we just verify the ADC pin
    // is configured and gives a plausible value (not rail-to-rail = open circuit).
    int raw = analogRead(_pin);
    _present = (raw > 50 && raw < (SOIL_ADC_RESOLUTION - 50));
    LOG_INFO(TAG, "init pin=%d raw=%d present=%s", _pin, raw, _present ? "YES" : "NO");
}

int SoilMoistureSensor::readRaw() {
#ifndef NATIVE_TEST
    return analogRead(_pin);
#else
    return (_dryAdc + _wetAdc) / 2;
#endif
}

float SoilMoistureSensor::readVoltage() {
    float v = (float)readRaw() / SOIL_ADC_RESOLUTION * (ADC_VREF_MV / 1000.0f);
    return v;
}

SensorResult SoilMoistureSensor::readPercent() {
    SensorResult r;
#ifdef MOCK_SENSORS
    // Realistic mock: slowly oscillating moisture between 20–40 %
    static float mock = 30.0f;
    static float dir  = 0.3f;
    mock += dir;
    if (mock > 42.0f || mock < 18.0f) dir = -dir;
    r.value  = mock;
    r.status = SensorStatus::MOCK;
    return r;
#endif

    if (!_present) { r.status = SensorStatus::NOT_FOUND; return r; }

    int raw = readRaw();
    r.value  = adcToPercent(raw);
    r.status = SensorStatus::OK;
    LOG_DBG(TAG, "raw=%d pct=%.1f", raw, r.value);
    return r;
}

void SoilMoistureSensor::setCalibration(int dryAdc, int wetAdc) {
    _dryAdc = dryAdc;
    _wetAdc = wetAdc;
    LOG_INFO(TAG, "Calibration updated dry=%d wet=%d", dryAdc, wetAdc);
}

float SoilMoistureSensor::adcToPercent(int raw) const {
    if (_dryAdc == _wetAdc) return 50.0f;
    // Higher ADC = drier for this sensor type
    float pct = (float)(_dryAdc - raw) / (_dryAdc - _wetAdc) * 100.0f;
    if (pct < 0.0f)   pct = 0.0f;
    if (pct > 100.0f) pct = 100.0f;
    return pct;
}
