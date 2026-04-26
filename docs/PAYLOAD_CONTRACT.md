# Payload Contract

## Backward-compatible flat payload (legacy)
```json
{
  "deviceId": "vineguard-node-001",
  "soilMoisture": 28.4,
  "soilTempC": null,
  "ambientTempC": 21.3,
  "ambientHumidity": 63.2,
  "lightLux": 245.0,
  "batteryVoltage": 3.97,
  "timestamp": 1714147200
}
```

## Canonical ingestor payload (current cloud)
```json
{
  "schema_version": "1.0",
  "device_id": "vg-node-001",
  "timestamp": 1714147200,
  "tier": "basic",
  "sensors": {
    "soil_moisture_pct": 28.4,
    "soil_temp_c": 18.2,
    "ambient_temp_c": 21.3,
    "ambient_humidity_pct": 63.2,
    "pressure_hpa": 1007.2,
    "light_lux": 245.0,
    "leaf_wetness_pct": null
  },
  "meta": {
    "battery_voltage": 3.97,
    "battery_pct": 78,
    "rssi": -78,
    "snr": 8.1,
    "sensor_ok": true
  }
}
```

## Enhanced metadata extension
Node firmware may include a `vineguard` object with `schemaVersion`, `firmwareVersion`, `sequence`, `bootCount`, `radioMode`, and deployment metadata. Gateway passes it through while preserving cloud-required fields.

## Normalization rules
1. If payload has `schema_version + sensors + meta`, publish unchanged.
2. If payload is legacy flat, publish unchanged.
3. If payload is enhanced nested (`readings` style), gateway maps into canonical v1.
4. Reject malformed/unsupported payloads.
