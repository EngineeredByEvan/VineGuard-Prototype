#include "LoRaRadioClient.h"

static const char* TAG = "LORA_P2P";

bool LoRaRadioClient::begin() {
#ifdef NATIVE_TEST
    _ready = true;
    return true;
#else
    return initRadio();
#endif
}

bool LoRaRadioClient::initRadio() {
#ifdef NATIVE_TEST
    _ready = true;
    return true;
#else
    // SPI bus must be initialised before RadioLib Module is constructed.
    SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);

    int16_t state = _radio.begin(
        LORA_FREQUENCY_MHZ,
        LORA_BANDWIDTH_KHZ,
        LORA_SPREADING_FACTOR,
        LORA_CODING_RATE,
        LORA_SYNC_WORD,
        LORA_TX_POWER_DBM
    );

    if (state != RADIOLIB_ERR_NONE) {
        LOG_ERR(TAG, "Radio init failed: %d", state);
        _ready = false;
        return false;
    }

    // Heltec V3 uses TCXO (temperature-compensated crystal)
    // Enable the TCXO voltage reference line
    state = _radio.setTCXO(1.8f);
    if (state != RADIOLIB_ERR_NONE) {
        // Non-fatal; some boards don't have TCXO
        LOG_DBG(TAG, "TCXO set returned %d (non-fatal)", state);
    }

    _ready = true;
    LOG_INFO(TAG, "SX1262 init OK %.1f MHz SF%d BW%.0fkHz",
             LORA_FREQUENCY_MHZ, LORA_SPREADING_FACTOR, LORA_BANDWIDTH_KHZ);
    return true;
#endif
}

bool LoRaRadioClient::send(const char* jsonPayload, size_t len) {
    if (!_ready) return false;
    return transmitJson(jsonPayload, len);
}

bool LoRaRadioClient::transmitJson(const char* json, size_t len) {
#ifdef NATIVE_TEST
    printf("[lora_p2p] TX %zu bytes: %s\n", len, json);
    return true;
#else
    // Build framed packet: 1-byte length + payload (truncated to 222 bytes)
    size_t txLen = len;
    if (txLen > 220) {
        LOG_ERR(TAG, "Payload too large (%zu), truncating to 220", txLen);
        txLen = 220;
    }

    int16_t state = _radio.transmit((uint8_t*)json, txLen);

    if (state == RADIOLIB_ERR_NONE) {
        LOG_INFO(TAG, "TX OK %zu bytes", txLen);
        return true;
    }

    LOG_ERR(TAG, "TX failed: %d", state);
    return false;
#endif
}
