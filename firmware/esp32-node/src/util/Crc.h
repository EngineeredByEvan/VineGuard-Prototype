#pragma once
#include <stdint.h>
#include <stddef.h>

namespace Crc {
    // CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
    // Used for VGPP binary payload integrity check.
    uint16_t crc16(const uint8_t* data, size_t len);
}
