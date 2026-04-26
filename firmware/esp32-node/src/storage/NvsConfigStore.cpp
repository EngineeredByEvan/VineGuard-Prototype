#include "NvsConfigStore.h"

bool NvsConfigStore::load(RuntimeConfig& cfg) {
  prefs_.begin("vgcfg", true);
  cfg.identity.deviceId = prefs_.getString("deviceId", cfg.identity.deviceId);
  cfg.identity.nodeSerial = prefs_.getString("serial", cfg.identity.nodeSerial);
  cfg.identity.vineyardId = prefs_.getString("vineyard", cfg.identity.vineyardId);
  cfg.identity.blockId = prefs_.getString("block", cfg.identity.blockId);
  cfg.identity.nodeType = prefs_.getString("nodeType", cfg.identity.nodeType);
  cfg.sampleIntervalSec = prefs_.getUInt("sampleSec", cfg.sampleIntervalSec);
  cfg.transmitIntervalSec = prefs_.getUInt("txSec", cfg.transmitIntervalSec);
  prefs_.end();
  return true;
}

bool NvsConfigStore::save(const RuntimeConfig& cfg) {
  prefs_.begin("vgcfg", false);
  prefs_.putString("deviceId", cfg.identity.deviceId);
  prefs_.putString("serial", cfg.identity.nodeSerial);
  prefs_.putString("vineyard", cfg.identity.vineyardId);
  prefs_.putString("block", cfg.identity.blockId);
  prefs_.putString("nodeType", cfg.identity.nodeType);
  prefs_.putUInt("sampleSec", cfg.sampleIntervalSec);
  prefs_.putUInt("txSec", cfg.transmitIntervalSec);
  prefs_.end();
  return true;
}
