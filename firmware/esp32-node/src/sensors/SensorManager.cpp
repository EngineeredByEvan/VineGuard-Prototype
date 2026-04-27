#include "SensorManager.h"

static const char* TAG = "SENSORS";

SensorManager::SensorManager()
    : _soil(PIN_SOIL_MOISTURE, SOIL_DRY_ADC_VALUE, SOIL_WET_ADC_VALUE),
      _bme(Wire, BME280_I2C_ADDR),
      _lux(Wire),
      _battery(PIN_BATTERY_ADC, BATTERY_DIVIDER_RATIO,
               BATTERY_VOLTAGE_MIN, BATTERY_VOLTAGE_MAX,
#if ENABLE_SOLAR_ADC
               PIN_SOLAR_ADC
#else
               0xFF
#endif
      )
#if ENABLE_LEAF_WETNESS
    , _leaf(Serial2, PIN_RS485_DE, RS485_MODBUS_ADDR)
#endif
{}

void SensorManager::begin() {
#ifndef NATIVE_TEST
    // External I2C bus for BME280 + VEML7700
    Wire.begin(PIN_EXT_I2C_SDA, PIN_EXT_I2C_SCL);
    Wire.setClock(100000);

    // Sensor power rail
    pinMode(PIN_SENSOR_POWER, OUTPUT);
    digitalWrite(PIN_SENSOR_POWER, LOW);
#endif

    // Power on briefly to allow sensor init
    powerOn();
    delay(SENSOR_WARMUP_MS);

    _soil.init();
    _bme.init();
    _lux.init();
    _battery.init();

#if ENABLE_LEAF_WETNESS
    _leaf.init();
#endif

    powerOff();

    LOG_INFO(TAG, "Sensors: soil=%s bme=%s lux=%s leaf=%s",
             _soil.isPresent()    ? "OK" : "MISS",
             _bme.isPresent()     ? "OK" : "MISS",
             _lux.isPresent()     ? "OK" : "MISS",
#if ENABLE_LEAF_WETNESS
             _leaf.isPresent()    ? "OK" : "MISS"
#else
             "DISABLED"
#endif
    );
}

bool SensorManager::sample(SensorReadings& out) {
    powerOn();
    delay(SENSOR_WARMUP_MS);

    // ── Soil ──────────────────────────────────────────────────────────────────
    SensorResult soilPct = _soil.readPercent();
    out.soilOk             = soilPct.ok();
    out.soilMoisturePercent = soilPct.value;
    out.soilMoistureRaw    = _soil.readRaw();
    out.soilVoltage        = _soil.readVoltage();

    // ── BME280 ────────────────────────────────────────────────────────────────
    Bme280Sensor::Reading env = _bme.read();
    out.bme280Ok          = env.ok;
    out.ambientTempC      = env.ok ? env.tempC    : -999.0f;
    out.ambientHumidityPct = env.ok ? env.humidity : -1.0f;
    out.pressureHpa       = env.ok ? env.pressure : -1.0f;
    out.dewPointC         = env.ok ? env.dewPoint : -999.0f;

    // ── Lux ───────────────────────────────────────────────────────────────────
    SensorResult lux = _lux.readLux();
    out.luxOk     = lux.ok();
    out.lightLux  = lux.ok() ? lux.value : -1.0f;

    // ── Leaf wetness ──────────────────────────────────────────────────────────
#if ENABLE_LEAF_WETNESS
    LeafWetnessSensor::Reading lw = _leaf.read();
    out.leafWetnessOk      = lw.ok;
    out.leafWetnessPercent = lw.ok ? lw.percent : -1.0f;
    out.leafWetnessRaw     = lw.ok ? lw.raw     : -1;
#else
    out.leafWetnessOk      = false;
    out.leafWetnessPercent = -1.0f;
    out.leafWetnessRaw     = -1;
#endif

    powerOff();

    // ── Battery (read after power rail off to avoid ADC noise) ───────────────
    BatteryMonitor::Reading batt = _battery.read();
    out.batteryOk       = batt.ok;
    out.batteryVoltage  = batt.battVoltage;
    out.batteryPercent  = batt.battPercent;
    out.solarVoltage    = batt.solarVoltage;

    bool anyOk = out.soilOk || out.bme280Ok || out.luxOk || out.batteryOk;
    LOG_INFO(TAG, "sample done: soil=%.1f%% T=%.1fC RH=%.1f%% lux=%.0f batt=%.2fV",
             out.soilMoisturePercent, out.ambientTempC,
             out.ambientHumidityPct, out.lightLux, out.batteryVoltage);
    return anyOk;
}

bool SensorManager::soilPresent()        const { return _soil.isPresent(); }
bool SensorManager::bme280Present()      const { return _bme.isPresent(); }
bool SensorManager::luxPresent()         const { return _lux.isPresent(); }
bool SensorManager::leafWetnessPresent() const {
#if ENABLE_LEAF_WETNESS
    return _leaf.isPresent();
#else
    return false;
#endif
}

void SensorManager::powerOn() {
#ifndef NATIVE_TEST
    digitalWrite(PIN_SENSOR_POWER, HIGH);
#endif
}

void SensorManager::powerOff() {
#ifndef NATIVE_TEST
    digitalWrite(PIN_SENSOR_POWER, LOW);
#endif
}
