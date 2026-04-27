#include "LeafWetnessSensor.h"

static const char* TAG = "LEAFWET";

// ─── Modbus RTU frame constants ───────────────────────────────────────────────
// Function code 0x03: Read Holding Registers
static constexpr uint8_t MB_FC_READ_HOLDING = 0x03;

// TODO (hardware-dependent): Confirm the correct holding register address
// from the leaf wetness sensor datasheet.
static constexpr uint16_t REG_WETNESS = 0x0000;

// TODO (hardware-dependent): Confirm whether the sensor outputs a raw ADC
// value (0–4095) or a scaled percent (0–100).
// Set SENSOR_OUTPUTS_PERCENT = true if the register already contains 0–100.
static constexpr bool SENSOR_OUTPUTS_PERCENT = false;
static constexpr int  RAW_MIN = 0;
static constexpr int  RAW_MAX = 4095;  // TODO: confirm from datasheet

LeafWetnessSensor::LeafWetnessSensor(HardwareSerial& serial, uint8_t dePin, uint8_t slaveAddr)
    : _serial(serial), _dePin(dePin), _slaveAddr(slaveAddr) {}

bool LeafWetnessSensor::init() {
#if ENABLE_LEAF_WETNESS == 0
    LOG_INFO(TAG, "Leaf wetness disabled at compile time");
    _present = false;
    return false;
#endif

#ifdef MOCK_SENSORS
    _present = true;
    LOG_INFO(TAG, "Mock mode");
    return true;
#endif

#ifdef NATIVE_TEST
    _present = true;
    return true;
#else
    pinMode(_dePin, OUTPUT);
    rxEnable();

    // TODO (hardware-dependent): Verify the correct baud rate and serial config.
    _serial.begin(RS485_BAUD_RATE, SERIAL_8N1);
    delay(50);

    // Probe the sensor with a read request
    int val = modbusReadRegister(REG_WETNESS);
    _present = (val >= 0);
    if (_present) {
        LOG_INFO(TAG, "Found at Modbus addr %d, raw=%d", _slaveAddr, val);
    } else {
        LOG_ERR(TAG, "No response from Modbus addr %d", _slaveAddr);
    }
    return _present;
#endif
}

LeafWetnessSensor::Reading LeafWetnessSensor::read() {
    Reading r;

#if ENABLE_LEAF_WETNESS == 0
    return r;
#endif

#ifdef MOCK_SENSORS
    // Simulate intermittent leaf wetness events
    static float wet = 10.0f;
    static float dir = 0.5f;
    wet += dir;
    if (wet > 80.0f || wet < 5.0f) dir = -dir;
    r.raw     = (int)(wet * 40);
    r.percent = wet;
    r.isWet   = wet >= WET_THRESHOLD_PCT;
    r.ok      = true;
    return r;
#endif

#ifdef NATIVE_TEST
    r.raw = 500; r.percent = 12.2f; r.isWet = false; r.ok = true;
    return r;
#else
    if (!_present) return r;

    int raw = modbusReadRegister(REG_WETNESS);
    if (raw < 0) {
        LOG_ERR(TAG, "Read timeout");
        _present = false;
        return r;
    }

    r.raw = raw;
    if (SENSOR_OUTPUTS_PERCENT) {
        r.percent = constrain((float)raw, 0.0f, 100.0f);
    } else {
        // TODO (hardware-dependent): Confirm RAW_MIN/RAW_MAX from datasheet
        r.percent = (float)(raw - RAW_MIN) / (RAW_MAX - RAW_MIN) * 100.0f;
        if (r.percent < 0.0f)   r.percent = 0.0f;
        if (r.percent > 100.0f) r.percent = 100.0f;
    }
    r.isWet = r.percent >= WET_THRESHOLD_PCT;
    r.ok    = true;
    LOG_DBG(TAG, "raw=%d pct=%.1f wet=%d", raw, r.percent, (int)r.isWet);
    return r;
#endif
}

// ─── Minimal Modbus RTU Read Holding Registers ───────────────────────────────
// TODO (hardware-dependent): If the sensor uses a non-standard framing,
// replace this function body with the correct command sequence.

void LeafWetnessSensor::txEnable()  {
#ifndef NATIVE_TEST
    digitalWrite(_dePin, HIGH);
    delayMicroseconds(100);
#endif
}

void LeafWetnessSensor::rxEnable() {
#ifndef NATIVE_TEST
    digitalWrite(_dePin, LOW);
#endif
}

static uint16_t crc16Modbus(const uint8_t* buf, uint8_t len) {
    uint16_t crc = 0xFFFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= buf[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 0x0001) ? (crc >> 1) ^ 0xA001 : (crc >> 1);
        }
    }
    return crc;
}

int LeafWetnessSensor::modbusReadRegister(uint16_t reg) {
#ifdef NATIVE_TEST
    return 500;
#else
    uint8_t req[8];
    req[0] = _slaveAddr;
    req[1] = MB_FC_READ_HOLDING;
    req[2] = (reg >> 8) & 0xFF;
    req[3] = reg & 0xFF;
    req[4] = 0x00;   // quantity hi
    req[5] = 0x01;   // quantity lo: read 1 register
    uint16_t crc = crc16Modbus(req, 6);
    req[6] = crc & 0xFF;
    req[7] = (crc >> 8) & 0xFF;

    // Flush RX buffer
    while (_serial.available()) _serial.read();

    txEnable();
    _serial.write(req, 8);
    _serial.flush();
    rxEnable();

    // Wait for response (slave addr + FC + byte count + 2 data bytes + 2 CRC)
    uint32_t start = millis();
    while (_serial.available() < 7) {
        if (millis() - start > RS485_TIMEOUT_MS) return -1;
        delay(1);
    }

    uint8_t rsp[7];
    _serial.readBytes(rsp, 7);

    // Validate CRC
    uint16_t rxCrc = (uint16_t)rsp[6] | ((uint16_t)rsp[5] << 8);
    if (crc16Modbus(rsp, 5) != rxCrc) {
        LOG_ERR(TAG, "CRC mismatch");
        return -1;
    }
    if (rsp[0] != _slaveAddr || rsp[1] != MB_FC_READ_HOLDING) {
        LOG_ERR(TAG, "Bad response frame");
        return -1;
    }

    return (int)((uint16_t)rsp[3] << 8 | rsp[4]);
#endif
}
