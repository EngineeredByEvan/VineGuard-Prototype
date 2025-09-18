#include "SensorInterfaces.h"

#include <Arduino.h>
#include <Wire.h>
#include <cmath>

#include <Adafruit_SHT31.h>
#include <BH1750.h>
#include <DallasTemperature.h>
#include <OneWire.h>

namespace {
#ifndef LAB_MODE
Adafruit_SHT31 sht31 = Adafruit_SHT31();
BH1750 lightMeter;
#endif
}

AnalogSoilMoistureSensor::AnalogSoilMoistureSensor(uint8_t pin, uint16_t dryRef, uint16_t wetRef)
    : pin_(pin), dryRef_(dryRef), wetRef_(wetRef) {}

bool AnalogSoilMoistureSensor::begin() {
    pinMode(pin_, INPUT);
    return true;
}

bool AnalogSoilMoistureSensor::read(SoilMoistureData &out) {
#ifdef LAB_MODE
    const float oscillation = 0.5f + 0.4f * sinf(millis() / 3000.0f);
    const uint16_t minRef = wetRef_ > dryRef_ ? dryRef_ : wetRef_;
    const uint16_t maxRef = wetRef_ > dryRef_ ? wetRef_ : dryRef_;
    const uint16_t span = maxRef - minRef;
    uint16_t raw = static_cast<uint16_t>(oscillation * span) + minRef;
#else
    uint16_t raw = analogRead(pin_);
#endif
    out.raw = raw;
    out.normalized = normalizeSensorReading(raw, dryRef_, wetRef_);
    return true;
}

SoilTemperatureSensor::SoilTemperatureSensor(uint8_t pin) : pin_(pin) {}

bool SoilTemperatureSensor::begin() {
#ifndef LAB_MODE
    oneWire_.reset(new OneWire(pin_));
    driver_.reset(new DallasTemperature(oneWire_.get()));
    driver_->begin();
#endif
    return true;
}

bool SoilTemperatureSensor::read(TemperatureData &out) {
#ifdef LAB_MODE
    out.temperatureC = 18.0f + 3.0f * sinf(millis() / 5000.0f);
    return true;
#else
    if (!driver_) {
        return false;
    }
    driver_->requestTemperatures();
    const float tempC = driver_->getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C) {
        return false;
    }
    out.temperatureC = tempC;
    return true;
#endif
}

bool AmbientClimateSensor::begin() {
    Wire.begin();
#ifndef LAB_MODE
    if (!sht31.begin(0x44)) {
        return false;
    }
#endif
    return true;
}

bool AmbientClimateSensor::read(AmbientClimateData &out) {
#ifdef LAB_MODE
    out.temperatureC = 22.0f + 1.5f * sinf(millis() / 4000.0f);
    out.humidity = 50.0f + 5.0f * cosf(millis() / 4500.0f);
    return true;
#else
    const float temp = sht31.readTemperature();
    const float humidity = sht31.readHumidity();
    if (isnan(temp) || isnan(humidity)) {
        return false;
    }
    out.temperatureC = temp;
    out.humidity = humidity;
    return true;
#endif
}

bool LightSensor::begin() {
    Wire.begin();
#ifndef LAB_MODE
    return lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
#else
    return true;
#endif
}

bool LightSensor::read(LightData &out) {
#ifdef LAB_MODE
    out.lux = 200.0f + 150.0f * sinf(millis() / 6000.0f);
    return true;
#else
    out.lux = lightMeter.readLightLevel();
    if (out.lux < 0) {
        return false;
    }
    return true;
#endif
}

BatteryMonitor::BatteryMonitor(uint8_t pin, uint16_t maxAdc, float referenceVoltage, float r1, float r2)
    : pin_(pin), maxAdc_(maxAdc), referenceVoltage_(referenceVoltage), r1_(r1), r2_(r2) {}

bool BatteryMonitor::begin() {
    pinMode(pin_, INPUT);
    return true;
}

bool BatteryMonitor::read(BatteryData &out) {
#ifdef LAB_MODE
    const float oscillation = 3.7f + 0.3f * sinf(millis() / 7000.0f);
    out.voltage = oscillation;
    return true;
#else
    const uint16_t raw = analogRead(pin_);
    out.voltage = computeBatteryVoltage(raw, maxAdc_, referenceVoltage_, r1_, r2_);
    return true;
#endif
}
