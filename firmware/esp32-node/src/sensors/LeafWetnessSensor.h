#pragma once
#include <Arduino.h>
#include "../../include/build_config.h"
#include "../../include/config.h"
#include "../util/Logger.h"
#include "SensorTypes.h"

// Optional Precision+ leaf wetness sensor via RS485 / Modbus RTU.
// Only compiled when ENABLE_LEAF_WETNESS=1.
//
// TODO (hardware-dependent): This driver contains a placeholder Modbus
// implementation.  The actual register map must be filled in once the
// physical sensor's datasheet is available.  See the TODO comments in
// LeafWetnessSensor.cpp for the exact insertion points.
//
// Assumptions:
//  - Sensor is a Modbus RTU slave on RS485 bus
//  - Slave address: RS485_MODBUS_ADDR (default 1)
//  - Holding register 0x00 = raw leaf wetness (0–4095 for 12-bit, or 0–100 for percent)
//  - RS485 half-duplex controlled by DE pin (HIGH=transmit, LOW=receive)

class LeafWetnessSensor {
public:
    LeafWetnessSensor(HardwareSerial& serial,
                      uint8_t dePin,
                      uint8_t slaveAddr = RS485_MODBUS_ADDR);

    bool init();
    bool isPresent() const { return _present; }

    struct Reading {
        float   percent = -1.0f;
        int     raw     = -1;
        bool    isWet   = false;   // true when percent > WET_THRESHOLD_PCT
        bool    ok      = false;
    };
    static constexpr float WET_THRESHOLD_PCT = 30.0f;

    Reading read();

private:
    HardwareSerial& _serial;
    uint8_t         _dePin;
    uint8_t         _slaveAddr;
    bool            _present = false;

    // Send a Modbus Read Holding Registers request and parse response.
    // Returns raw register value or -1 on error/timeout.
    int modbusReadRegister(uint16_t reg);

    void txEnable();
    void rxEnable();
};
