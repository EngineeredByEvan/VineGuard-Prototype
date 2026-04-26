# OTA Strategy

MVP ships OTA disabled by default for LoRa-only field nodes.

Current:
- Firmware exposes OTA check hook (`OtaUpdater`) but does not auto-update.
- Updates are performed physically (USB/serial) during pilot phase.

Future:
- Wi-Fi assisted HTTPS OTA with cert pinning.
- Signed manifest + firmware checksum validation.
- Battery-aware update gating (skip below safe threshold).
- Gateway-assisted staged rollout planning.
