#include "Bme280Sensor.h"
#include "../util/TimeUtil.h"

static const char* TAG = "BME280";

Bme280Sensor::Bme280Sensor(TwoWire& wire, uint8_t addr)
    : _addr(addr), _wire(wire) {}

bool Bme280Sensor::init() {
#ifdef MOCK_SENSORS
    _present = true;
    LOG_INFO(TAG, "Mock mode");
    return true;
#endif

#ifdef NATIVE_TEST
    _present = true;
    return true;
#else
    _present = _bme.begin(_addr, &_wire);
    if (_present) {
        // Weather monitoring: low oversampling, 1-shot mode
        _bme.setSampling(Adafruit_BME280::MODE_FORCED,
                         Adafruit_BME280::SAMPLING_X1,
                         Adafruit_BME280::SAMPLING_X1,
                         Adafruit_BME280::SAMPLING_X1,
                         Adafruit_BME280::FILTER_OFF);
        LOG_INFO(TAG, "Found at 0x%02X", _addr);
    } else {
        LOG_ERR(TAG, "Not found at 0x%02X – check wiring and I2C address", _addr);
    }
    return _present;
#endif
}

Bme280Sensor::Reading Bme280Sensor::read() {
    Reading r;

#ifdef MOCK_SENSORS
    // Realistic diurnal temperature cycle with slight drift
    static float temp     = 18.0f;
    static float humidity = 65.0f;
    static float pressure = 1013.0f;
    static float tDir = 0.05f;
    static float hDir = -0.02f;
    temp     += tDir; if (temp > 30.0f || temp < 10.0f) tDir = -tDir;
    humidity += hDir; if (humidity > 90.0f || humidity < 40.0f) hDir = -hDir;
    r.tempC    = temp;
    r.humidity = humidity;
    r.pressure = pressure + ((float)(millis() % 100) / 100.0f - 0.5f);
    r.dewPoint = TimeUtil::dewPoint(r.tempC, r.humidity);
    r.ok = true;
    return r;
#endif

#ifdef NATIVE_TEST
    r.tempC    = 20.0f;
    r.humidity = 60.0f;
    r.pressure = 1013.25f;
    r.dewPoint = TimeUtil::dewPoint(r.tempC, r.humidity);
    r.ok = true;
    return r;
#else
    if (!_present) return r;

    // Force a single measurement
    _bme.takeForcedMeasurement();

    r.tempC    = _bme.readTemperature();
    r.humidity = _bme.readHumidity();
    r.pressure = _bme.readPressure() / 100.0f;  // Pa → hPa
    r.dewPoint = TimeUtil::dewPoint(r.tempC, r.humidity);

    // Sanity check (BME280 returns 0 or NaN on bus error)
    r.ok = (r.tempC > -40.0f && r.tempC < 85.0f &&
            r.humidity >= 0.0f && r.humidity <= 100.0f &&
            r.pressure > 800.0f && r.pressure < 1100.0f);

    LOG_DBG(TAG, "T=%.2f H=%.2f P=%.2f Td=%.2f ok=%d",
            r.tempC, r.humidity, r.pressure, r.dewPoint, (int)r.ok);
    return r;
#endif
}
