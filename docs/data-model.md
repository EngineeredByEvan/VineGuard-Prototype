# Data Model

## Telemetry Payload

```json
{
  "deviceId": "vineguard-node-001",
  "soilMoisture": 57.2,
  "soilTempC": 18.5,
  "ambientTempC": 21.3,
  "ambientHumidity": 63.2,
  "lightLux": 245.0,
  "batteryVoltage": 3.97,
  "timestamp": 1700000000
}
```

## Database Tables

### telemetry_readings

| column            | type      | notes                                   |
|-------------------|-----------|-----------------------------------------|
| id                | UUID      | generated via `gen_random_uuid()`       |
| device_id         | text      | node identifier                         |
| soil_moisture     | float     | percentage (0-100)                      |
| soil_temp_c       | float     | Celsius                                 |
| ambient_temp_c    | float     | Celsius                                 |
| ambient_humidity  | float     | percentage                              |
| light_lux         | float     | lux                                     |
| battery_voltage   | float     | volts                                   |
| recorded_at       | timestamptz | hypertable dimension (Timescale)     |

### analytics_signals

| column      | type        | notes                                  |
|-------------|-------------|----------------------------------------|
| id          | UUID        | generated via `gen_random_uuid()`      |
| device_id   | text        | node identifier                        |
| signal_type | text        | e.g. `low_moisture`, `disease_risk`    |
| severity    | text        | info/warning/critical                  |
| description | text        | human readable insight                 |
| created_at  | timestamptz | defaults to `now()`                    |

## Retention

TimescaleDB policies can be added to downsample or drop data beyond 2 years
based on business needs. Analytics signals persist for historical reporting.
