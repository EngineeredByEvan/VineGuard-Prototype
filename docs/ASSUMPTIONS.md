# Assumptions

- Existing cloud ingestor contract is canonical `schema_version=1.0` payload with nested `sensors`/`meta`; legacy camelCase remains accepted.
- LoRaWAN OTAA radio bring-up requires board-specific RadioLib tuning and gateway/network server details not present in this repo.
- Leaf wetness RS485 command map is vendor-specific and not yet supplied.
- MVP prioritizes reliable telemetry ingestion compatibility over full LoRaWAN production hardening in this change set.
