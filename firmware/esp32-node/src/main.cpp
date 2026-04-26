#include <Arduino.h>

#include "app/AppController.h"

AppController app;

void setup() {
  Serial.begin(115200);
  delay(500);
  app.setup();
}

void loop() { app.runCycle(); }
