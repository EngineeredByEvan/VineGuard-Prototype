#pragma once

#include <Arduino.h>
#include <memory>

#include "SensorMath.h"

struct SoilMoistureData {
    uint16_t raw;
    float normalized;
};

struct TemperatureData {
    float temperatureC;
};

struct AmbientClimateData {
    float temperatureC;
    float humidity;
};

struct LightData {
    float lux;
};

struct BatteryData {
    float voltage;
};

template <typename T>
class ISensor {
   public:
    virtual ~ISensor() = default;
    virtual bool begin() = 0;
    virtual bool read(T &out) = 0;
};

class AnalogSoilMoistureSensor : public ISensor<SoilMoistureData> {
   public:
    AnalogSoilMoistureSensor(uint8_t pin, uint16_t dryRef, uint16_t wetRef);
    bool begin() override;
    bool read(SoilMoistureData &out) override;

   private:
    uint8_t pin_;
    uint16_t dryRef_;
    uint16_t wetRef_;
};

class SoilTemperatureSensor : public ISensor<TemperatureData> {
   public:
    explicit SoilTemperatureSensor(uint8_t pin);
    bool begin() override;
    bool read(TemperatureData &out) override;

   private:
    uint8_t pin_;
    std::unique_ptr<class OneWire> oneWire_;
    std::unique_ptr<class DallasTemperature> driver_;
};

class AmbientClimateSensor : public ISensor<AmbientClimateData> {
   public:
    bool begin() override;
    bool read(AmbientClimateData &out) override;
};

class LightSensor : public ISensor<LightData> {
   public:
    bool begin() override;
    bool read(LightData &out) override;
};

class BatteryMonitor : public ISensor<BatteryData> {
   public:
    BatteryMonitor(uint8_t pin, uint16_t maxAdc, float referenceVoltage, float r1, float r2);
    bool begin() override;
    bool read(BatteryData &out) override;

   private:
    uint8_t pin_;
    uint16_t maxAdc_;
    float referenceVoltage_;
    float r1_;
    float r2_;
};

struct SensorSnapshot {
    SoilMoistureData soilMoisture;
    TemperatureData soilTemperature;
    AmbientClimateData ambient;
    LightData light;
    BatteryData battery;
};
