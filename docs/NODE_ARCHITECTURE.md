# Node Architecture

- `AppController`: boots config, sensor manager, uplink, sleep policy.
- `SensorManager`: soil, BME280, lux, optional leaf wetness, battery.
- `TelemetryBuilder`: emits canonical v1 + legacy compatibility payloads.
- `UplinkClient` implementations: serial debug, LoRa P2P scaffold, LoRaWAN OTAA scaffold.
- `FailsafeQueue`: bounded in-memory retransmit queue.
- `NvsConfigStore`: runtime identity and interval overrides persisted in NVS.

Cycle: wake -> power sensor rail -> sample -> build payload -> uplink/retry queue -> OTA check (disabled default) -> deep sleep.
