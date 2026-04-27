#include "BatteryMonitor.h"
#include "../util/TimeUtil.h"

static const char* TAG = "BATT";

BatteryMonitor::BatteryMonitor(uint8_t battPin, float dividerRatio,
                                float vMin, float vMax, uint8_t solarPin)
    : _battPin(battPin), _solarPin(solarPin),
      _dividerRatio(dividerRatio), _vMin(vMin), _vMax(vMax) {}

void BatteryMonitor::init() {
#ifndef NATIVE_TEST
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);
    pinMode(_battPin, INPUT);
    if (_solarPin != 0xFF) pinMode(_solarPin, INPUT);
#endif
    LOG_INFO(TAG, "init battPin=%d ratio=%.2f Vmin=%.1f Vmax=%.1f",
             _battPin, _dividerRatio, _vMin, _vMax);
}

float BatteryMonitor::adcToVoltage(int raw) const {
    float adcV = (float)raw / 4095.0f * (ADC_VREF_MV / 1000.0f);
    return adcV * _dividerRatio;
}

BatteryMonitor::Reading BatteryMonitor::read() {
    Reading r;

#ifdef MOCK_SENSORS
    static float v = 11.8f;
    static float dir = -0.005f;
    v += dir;
    if (v < 9.5f || v > 12.5f) dir = -dir;
    r.battVoltage  = v;
    r.battPercent  = TimeUtil::batteryPercentFromVoltage(v, _vMin, _vMax);
    r.solarVoltage = ENABLE_SOLAR_ADC ? 13.2f : -1.0f;
    r.lowBattery   = v < BATTERY_LOW_THRESHOLD_V;
    r.critical     = v < BATTERY_CRITICAL_THRESHOLD_V;
    r.ok           = true;
    return r;
#endif

#ifdef NATIVE_TEST
    r.battVoltage  = 11.5f;
    r.battPercent  = 65;
    r.solarVoltage = -1.0f;
    r.ok           = true;
    return r;
#else
    // Average 4 readings to reduce ADC noise
    int sum = 0;
    for (int i = 0; i < 4; i++) {
        sum += analogRead(_battPin);
        delay(2);
    }
    r.battVoltage = adcToVoltage(sum / 4);
    r.battPercent = TimeUtil::batteryPercentFromVoltage(r.battVoltage, _vMin, _vMax);
    r.lowBattery  = r.battVoltage < BATTERY_LOW_THRESHOLD_V;
    r.critical    = r.battVoltage < BATTERY_CRITICAL_THRESHOLD_V;

#if ENABLE_SOLAR_ADC
    if (_solarPin != 0xFF) {
        int solarSum = 0;
        for (int i = 0; i < 4; i++) {
            solarSum += analogRead(_solarPin);
            delay(2);
        }
        r.solarVoltage = adcToVoltage(solarSum / 4);
    }
#else
    r.solarVoltage = -1.0f;
#endif

    r.ok = true;
    LOG_DBG(TAG, "V=%.2f pct=%d solar=%.2f low=%d",
            r.battVoltage, r.battPercent, r.solarVoltage, (int)r.lowBattery);
    return r;
#endif
}
