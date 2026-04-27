#include <Arduino.h>
#include "app/AppController.h"

// VineGuard Node Firmware v0.1.0
// Build environments: debug_serial | lora_p2p | lorawan_otaa
// See firmware/esp32-node/README.md for build and flash instructions.

static AppController app;

void setup() {
    app.setup();
}

void loop() {
    app.loop();
    // In USE_DEEP_SLEEP=1 mode, app.loop() never returns.
    // In debug/polling mode it returns after a blocking delay.
}
