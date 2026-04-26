# Provisioning

1. Create `firmware/esp32-node/tools/provisioning_manifest.csv` from example.
2. Run key generation:
   - `python3 firmware/esp32-node/tools/make_keys_header.py --manifest ... --serial VG-001`
3. Flash:
   - Bash: `firmware/esp32-node/tools/flash_device.sh VG-001`
   - PowerShell: `firmware/esp32-node/tools/flash_device.ps1 -Serial VG-001`
4. Label the enclosure with serial, device_id, DevEUI.

Security:
- Never commit `include/lorawan_keys.h`.
- AppKey is masked unless `--show-secrets` is provided.
- Use publish-only MQTT credentials for gateways.
