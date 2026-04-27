#pragma once
#include <Arduino.h>
#include "../../include/config.h"
#include "../util/Logger.h"

// Simple FIFO queue backed by SPIFFS for unsent telemetry payloads.
// Survives deep sleep.  Payloads are stored as newline-delimited JSON.
// On reconnect, AppController drains the queue before sending fresh data.

class FailsafeQueue {
public:
    explicit FailsafeQueue(const char* path = "/vg_queue.jsonl");

    bool begin();   // mount SPIFFS and recover existing queue
    void push(const char* jsonPayload);
    bool pop(String& out);   // returns false when empty
    bool isEmpty() const;
    int  depth() const { return _depth; }
    void clear();

private:
    const char* _path;
    int         _depth = 0;

    void recount();
};
