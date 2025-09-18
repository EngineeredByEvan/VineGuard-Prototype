#include "StatusLed.h"

StatusLed::StatusLed(uint8_t pin, bool activeHigh)
    : pin_(pin), activeHigh_(activeHigh), pattern_(LedPattern::Off), patternStart_(0), lastState_(false) {}

void StatusLed::begin() {
    pinMode(pin_, OUTPUT);
    applyState(false);
    patternStart_ = millis();
}

void StatusLed::setPattern(LedPattern pattern) {
    if (pattern_ == pattern) {
        return;
    }
    pattern_ = pattern;
    patternStart_ = millis();
}

void StatusLed::update() {
    const uint32_t now = millis();
    bool on = false;

    switch (pattern_) {
        case LedPattern::Off:
            on = false;
            break;
        case LedPattern::Ok: {
            const uint32_t position = (now - patternStart_) % 2000U;
            on = position < 150U;
            break;
        }
        case LedPattern::Error: {
            const uint32_t position = (now - patternStart_) % 2000U;
            on = (position < 150U) || (position >= 300U && position < 450U);
            break;
        }
        case LedPattern::Ota: {
            const uint32_t position = (now - patternStart_) % 600U;
            on = position < 300U;
            break;
        }
    }

    if (on != lastState_) {
        applyState(on);
        lastState_ = on;
    }
}

void StatusLed::applyState(bool on) {
    digitalWrite(pin_, activeHigh_ ? (on ? HIGH : LOW) : (on ? LOW : HIGH));
}
