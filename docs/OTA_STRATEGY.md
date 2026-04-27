# VineGuard OTA Firmware Update Strategy

## MVP Status

OTA is **stubbed** in the current firmware. `OtaUpdater::checkAndApply()` returns `false` immediately. `OTA_ENABLED = 0` in `config.h`.

For the LoRa-only MVP, OTA over LoRa is **out of scope**. Firmware updates require a USB cable and a laptop running PlatformIO.

---

## Why OTA Is Deferred for LoRa MVP

| Constraint | Detail |
|-----------|--------|
| LoRa payload size | Max 222 bytes at SF7, 51 bytes at SF10. An ESP32 firmware binary is ~1–2 MB — tens of thousands of LoRa packets. |
| Duty cycle | US915 has no mandatory duty cycle, but network server fair-use and battery constraints limit sustained downlink throughput. |
| LoRaWAN downlink size | LoRaWAN downlink (RX1/RX2) is limited to a few hundred bytes per day for most network plans. |
| Security complexity | Secure FUOTA requires fragmentation, CRC, signature verification — significant firmware complexity. |

---

## Interim Update Process (MVP)

Until OTA is implemented, update firmware via USB during a scheduled maintenance visit:

1. Bring a laptop with PlatformIO installed to the vineyard.
2. Open the node enclosure, connect USB-C cable to the Heltec V3.
3. Run the provisioning/flash tool:
   ```bash
   ./tools/flash_device.sh --serial VG-000001 --env lora_p2p
   ```
4. Run the serial smoke test to confirm new firmware is operating correctly:
   ```bash
   python tools/serial_smoke_test.py --port /dev/ttyUSB0
   ```
5. Reseal enclosure, verify telemetry appears in dashboard within one sample interval.

**Schedule**: Plan firmware updates during low-risk agronomic periods (not during frost risk windows or mildew spray windows).

---

## Medium Term: Wi-Fi-Assisted OTA

Nodes don't have Wi-Fi in the field, but can be updated via a maintenance laptop acting as a local Wi-Fi AP:

1. **Laptop AP** — laptop creates a Wi-Fi hotspot.
2. **Node connects temporarily** — add Wi-Fi credentials at build time (maintenance build only; separate environment `wifi_ota`).
3. **OTA flow**:
   - Node calls `esp_https_ota()` with `OTA_URL` pointing to the laptop's local HTTPS server.
   - Manifest endpoint returns current version + binary URL.
   - Node compares `FW_VERSION_STR` with manifest version.
   - If newer: download binary, verify SHA256, call `esp_ota_set_boot_partition()`, reboot.

**Safety rules (must enforce in code):**
- Never apply OTA if `batteryVoltage < BATTERY_LOW_THRESHOLD_V`.
- Verify SHA256 checksum of downloaded binary before writing to OTA partition.
- Use HTTPS with cert pinning or CA validation (`esp_http_client_set_cert_pem`).
- Do not update during the active sensor sampling window.
- Use ESP-IDF's native OTA partition rollback: if the new firmware crashes on first boot, the bootloader reverts to the previous image.

**OtaUpdater.cpp** has the full TODO checklist at the implementation point.

---

## Long Term: LoRaWAN FUOTA (TS006)

The LoRaWAN FUOTA (Firmware Update Over The Air) standard (TS006) enables multi-fragment firmware delivery over LoRaWAN downlinks. ChirpStack v4 has experimental FUOTA support.

High-level flow:
1. Network server initiates fragmentation session via multicast or unicast downlinks.
2. Node receives binary fragments on a dedicated FPort.
3. Node reassembles fragments using a redundancy algorithm (Reed-Solomon or XOR).
4. Node verifies CRC and signature, then applies update.

**Requirements before FUOTA is viable:**
- ChirpStack v4 deployed with FUOTA server plugin.
- Firmware compiled with FUOTA fragment handler (not yet implemented).
- Battery budget for sustained downlink reception (power budget analysis needed).
- Code signing infrastructure (keys, CI pipeline).

This is tracked as a future enhancement. The modular firmware architecture supports adding FUOTA without rewriting the core application.

---

## Version Tracking

`FW_VERSION_STR` is defined in `include/build_config.h`:
```cpp
#define FW_VERSION_MAJOR 0
#define FW_VERSION_MINOR 1
#define FW_VERSION_PATCH 0
#define FW_VERSION_STR   "0.1.0"
```

The version is reported in every telemetry payload (`firmware_version` field) and visible in the VineGuard dashboard node detail page. When updating firmware, increment the version before building.

---

## Recommended Next Steps

1. Implement a `/api/v1/firmware/latest` endpoint in the cloud API that returns `{"version":"x.y.z","sha256":"...","url":"..."}`.
2. Implement `OtaUpdater::checkAndApply()` using `esp_https_ota.h`.
3. Add a `wifi_ota` PlatformIO environment that enables Wi-Fi and OTA.
4. Test the full OTA flow on a bench node before deploying to field nodes.
5. Add firmware version to the node registry in the database so the dashboard can show stale-firmware alerts.
