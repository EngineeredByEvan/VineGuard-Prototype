#include "FailsafeQueue.h"

#ifndef NATIVE_TEST
  #include <SPIFFS.h>
#endif

static const char* TAG = "QUEUE";

FailsafeQueue::FailsafeQueue(const char* path) : _path(path) {}

bool FailsafeQueue::begin() {
#ifdef NATIVE_TEST
    _depth = 0;
    return true;
#else
    if (!SPIFFS.begin(true)) {
        LOG_ERR(TAG, "SPIFFS mount failed");
        return false;
    }
    recount();
    LOG_INFO(TAG, "Queue ready, depth=%d", _depth);
    return true;
#endif
}

void FailsafeQueue::push(const char* jsonPayload) {
    if (_depth >= FAILSAFE_QUEUE_MAX_DEPTH) {
        LOG_ERR(TAG, "Queue full (%d), dropping oldest", _depth);
        // Drop the oldest entry to make room
        String discard;
        pop(discard);
    }
#ifndef NATIVE_TEST
    File f = SPIFFS.open(_path, "a");
    if (!f) { LOG_ERR(TAG, "Cannot open queue for append"); return; }
    f.println(jsonPayload);
    f.close();
#endif
    _depth++;
    LOG_DBG(TAG, "Push depth=%d", _depth);
}

bool FailsafeQueue::pop(String& out) {
    if (_depth == 0) return false;
#ifdef NATIVE_TEST
    out = "{}";
    _depth = (_depth > 0) ? _depth - 1 : 0;
    return true;
#else
    File f = SPIFFS.open(_path, "r");
    if (!f) return false;

    // Read first line
    out = f.readStringUntil('\n');
    out.trim();

    // Read remaining lines into a temp buffer, then rewrite without the first
    String remainder = "";
    while (f.available()) {
        String line = f.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            remainder += line + "\n";
        }
    }
    f.close();

    File fw = SPIFFS.open(_path, "w");
    if (fw) {
        fw.print(remainder);
        fw.close();
    }

    _depth = (_depth > 0) ? _depth - 1 : 0;
    LOG_DBG(TAG, "Pop depth=%d", _depth);
    return out.length() > 0;
#endif
}

bool FailsafeQueue::isEmpty() const {
    return _depth == 0;
}

void FailsafeQueue::clear() {
#ifndef NATIVE_TEST
    SPIFFS.remove(_path);
#endif
    _depth = 0;
    LOG_INFO(TAG, "Queue cleared");
}

void FailsafeQueue::recount() {
    _depth = 0;
#ifndef NATIVE_TEST
    File f = SPIFFS.open(_path, "r");
    if (!f) return;
    while (f.available()) {
        String line = f.readStringUntil('\n');
        if (line.trim().length() > 0) _depth++;
    }
    f.close();
#endif
}
