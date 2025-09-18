#pragma once

#include <Arduino.h>

enum class LedPattern { Off, Ok, Error, Ota };

class StatusLed {
   public:
    StatusLed(uint8_t pin, bool activeHigh = true);
    void begin();
    void setPattern(LedPattern pattern);
    void update();

   private:
    void applyState(bool on);

    uint8_t pin_;
    bool activeHigh_;
    LedPattern pattern_;
    uint32_t patternStart_;
    bool lastState_;
};
