#pragma once
#include <Preferences.h>

#include "config.h"

class NvsConfigStore {
 public:
  bool load(RuntimeConfig& cfg);
  bool save(const RuntimeConfig& cfg);

 private:
  Preferences prefs_;
};
