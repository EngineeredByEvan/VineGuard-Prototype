# VineGuard Telemetry Payload Contract

**Last updated:** 2026-04-27  
**Schema version:** 1.0  
**Status:** Authoritative — all components must conform to this document.

---

## 1. Overview

VineGuard nodes can produce telemetry in three wire formats, depending on the
firmware build mode and hardware configuration:

| Format | Produced by | Consumed by | Description |
|--------|-------------|-------------|-------------|
| **V1 JSON** | All build modes (canonical) | MQTT ingestor, dashboard | Primary cloud format; published to `vineguard/telemetry` |
| **Compact LoRa P2P JSON** | `BUILD_MODE_LORA_P2P` firmware | Gateway (`serial_json` mode) | Abbreviated keys to minimise over-the-air bytes |
| **Binary VGPP-1 Frame** | `BUILD_MODE_LORAWAN_OTAA` firmware | Gateway (`serial_binary` / ChirpStack) | 22–25 byte packed binary with CRC |

The **gateway is responsible for normalising** all three formats into V1 JSON
before publishing to MQTT. The ingestor and analytics service only ever receive
V1 JSON (or the legacy camelCase format described in §5 for backwards
compatibility).

---

## 2. V1 JSON Schema

### 2.1 Example payload

```json
{
  "schema_version": "1.0",
  "device_id": "vg-node-003",
  "gateway_id": "vg-gw-001",
  "timestamp": 1745712000,
  "tier": "precision_plus",
  "sensors": {
    "soil_moisture_pct":    38.5,
    "soil_temp_c":          null,
    "ambient_temp_c":       19.2,
    "ambient_humidity_pct": 88.0,
    "pressure_hpa":         1003.5,
    "light_lux":            8200.0,
    "leaf_wetness_pct":     72.0
  },
  "meta": {
    "battery_voltage": 11.9,
    "battery_pct":     78,
    "rssi":            -70,
    "snr":             11.2,
    "sensor_ok":       true
  }
}
```

### 2.2 Field reference

#### Top-level fields

| Field | Type | Constraints | Nullable | Notes |
|-------|------|-------------|----------|-------|
| `schema_version` | `string` | Must be `"1.0"` | No | Increment when a breaking change is made |
| `device_id` | `string` | 4–64 chars; `[a-zA-Z0-9_-]` | No | Must match the `device_id` registered in the `nodes` table |
| `gateway_id` | `string` | 4–64 chars | Yes | Injected by the gateway; null if the node published directly via LoRaWAN without a VineGuard gateway |
| `timestamp` | `integer` | Unix epoch (seconds, UTC) | No | If absent or zero the gateway substitutes the arrival time |
| `tier` | `string` | `"basic"` or `"precision_plus"` | No | Controls which sensor fields are expected |

#### `sensors` object

| Field | Type | Range | Nullable | Notes |
|-------|------|-------|----------|-------|
| `soil_moisture_pct` | `float` | 0–100 | Yes | Derived from DFRobot SEN0308 capacitive probe; null if probe not fitted or read failed |
| `soil_temp_c` | `float` | −40 to 80 | Yes | **Reserved — always `null` in MVP.** Intended for DS18B20 probe; not wired |
| `ambient_temp_c` | `float` | −40 to 85 | Yes | BME280; null if BME280 not responding |
| `ambient_humidity_pct` | `float` | 0–100 | Yes | BME280; null if BME280 not responding |
| `pressure_hpa` | `float` | 850–1100 | Yes | BME280; null if BME280 not responding |
| `light_lux` | `float` | 0–200 000 | Yes | VEML7700; null if sensor not fitted or read failed |
| `leaf_wetness_pct` | `float` | 0–100 | Yes | RS485 Modbus probe; **precision_plus nodes only**; always null on basic tier |

#### `meta` object

| Field | Type | Range | Nullable | Notes |
|-------|------|-------|----------|-------|
| `battery_voltage` | `float` | 0–25 V | No | Measured via on-board ADC voltage divider |
| `battery_pct` | `integer` | 0–100 | Yes | Estimated from voltage curve; null if estimation not available |
| `rssi` | `integer` | — | Yes | Received Signal Strength Indicator (dBm); set by gateway from LoRa radio; null in mock mode |
| `snr` | `float` | — | Yes | Signal-to-Noise Ratio (dB); null if unavailable |
| `sensor_ok` | `boolean` | — | No | `true` if all expected sensors read successfully; `false` if any sensor failed |

### 2.3 MQTT topic

```
vineguard/telemetry
```

All nodes (regardless of tier or gateway) publish to this single topic. The
ingestor subscribes with QoS 1. The gateway publishes with QoS 1.

---

## 3. Compact LoRa P2P JSON

Used by `BUILD_MODE_LORA_P2P` firmware builds to keep the over-the-air packet
as small as possible (~130 bytes vs ~250 bytes for full V1 JSON). The gateway
receives these on the USB serial port (prefixed with `VGPAYLOAD:`) and expands
them to V1 before MQTT publish.

### 3.1 Key mapping

| Compact key | V1 field | Notes |
|-------------|----------|-------|
| `v` | `schema_version` | Always `"1.0"` |
| `id` | `device_id` | Full device_id string |
| `seq` | _(internal `_sequence`)_ | Sequence counter; not published to MQTT |
| `tier` | `tier` | `"basic"` or `"precision_plus"` |
| `sm` | `sensors.soil_moisture_pct` | |
| `st` | `sensors.soil_temp_c` | Reserved; always absent/null in MVP |
| `at` | `sensors.ambient_temp_c` | |
| `ah` | `sensors.ambient_humidity_pct` | |
| `p` | `sensors.pressure_hpa` | |
| `l` | `sensors.light_lux` | |
| `lw` | `sensors.leaf_wetness_pct` | precision_plus only |
| `bv` | `meta.battery_voltage` | |
| `bp` | `meta.battery_pct` | |
| `sv` | _(not in V1 top-level)_ | Solar voltage; stored in meta but not in DB |
| `ok` | `meta.sensor_ok` | Integer `1`/`0`; gateway converts to bool |

### 3.2 Example compact payload (serial line)

```
VGPAYLOAD:{"v":"1.0","id":"vg-node-001","seq":42,"tier":"basic","sm":28.4,"at":21.3,"ah":63.2,"p":1007.2,"l":24500.0,"bv":11.5,"bp":65,"ok":1}
```

The `VGPAYLOAD:` prefix is stripped by the gateway's `decode_auto()` function
before JSON parsing.

### 3.3 Gateway expansion

The gateway calls `decode_compact_json()` which:

1. Parses JSON.
2. Expands abbreviated keys to canonical names using `COMPACT_KEY_MAP`.
3. Sets `gateway_id` from the gateway's own `GATEWAY_ID` environment variable.
4. Substitutes the current UTC epoch for `timestamp` (compact format does not
   include a timestamp to save bytes).
5. Emits a complete V1 dict.

Fields absent from the compact packet are set to `null` in the V1 output.

---

## 4. Binary VGPP-1 Frame

Used by `BUILD_MODE_LORAWAN_OTAA` firmware and for future LoRaWAN FPort 1
uplinks. Defined in `firmware/esp32-node/include/payload_schema.h`.

### 4.1 Frame layout

All multi-byte integers are **little-endian**.

| Byte offset | Size (bytes) | Field | Encoding |
|-------------|-------------|-------|----------|
| 0 | 1 | Protocol ID | Fixed `0xA1` (VGPP-1 magic byte) |
| 1 | 2 | Sequence number (`seq`) | `uint16 LE` |
| 3 | 2 | Flags | `uint16 LE` bitfield (see §4.2) |
| 5 | 2 | `soil_moisture_x100` | `uint16 LE`; value = moisture % × 100 (0–10000) |
| 7 | 2 | `soil_temp_encoded` | `uint16 LE`; value = (°C + 40) × 10; 0–1200 |
| 9 | 2 | `ambient_temp_encoded` | `uint16 LE`; value = (°C + 40) × 10 |
| 11 | 2 | `ambient_humidity_x100` | `uint16 LE`; value = humidity % × 100 (0–10000) |
| 13 | 2 | `pressure_x10_m8500` | `uint16 LE`; value = (hPa × 10) − 8500; 0–2500 |
| 15 | 3 | `light_lux` | `uint24 LE`; raw lux value 0–200 000 |
| 18 | 1 | `battery_voltage_x10` | `uint8`; value = V × 10; range 0–25.5 V |
| 19 | 1 | `battery_pct` | `uint8`; 0–100 |
| [20] | [2] | `leaf_wetness_x100` | `uint16 LE`; only present if `FLAGS_LEAF_WETNESS_VALID` set |
| [22] | [1] | `solar_voltage_x10` | `uint8`; only present if `FLAGS_SOLAR_VALID` set |
| * | 2 | CRC-16/CCITT-FALSE | Always the last 2 bytes; covers all preceding bytes |

- **Minimum frame length:** 22 bytes (neither optional field present)
- **Maximum frame length:** 25 bytes (both optional fields present)

The CRC polynomial is `0x1021`, initial value `0xFFFF`, no reflection
(CRC-16/CCITT-FALSE). The gateway's `_crc16_ccitt()` function implements this
and verifies the frame before decoding.

### 4.2 Flags bitfield

| Bit | Mask | Name | Meaning |
|-----|------|------|---------|
| 0 | `0x0001` | `FLAGS_SOIL_VALID` | `soil_moisture_x100` field is valid |
| 1 | `0x0002` | `FLAGS_SOIL_TEMP_VALID` | `soil_temp_encoded` field is valid (reserved, normally 0) |
| 2 | `0x0004` | `FLAGS_BME280_VALID` | Ambient temp, humidity, and pressure fields are valid |
| 3 | `0x0008` | `FLAGS_LUX_VALID` | `light_lux` field is valid |
| 4 | `0x0010` | `FLAGS_LEAF_WETNESS_VALID` | Optional `leaf_wetness_x100` field is appended |
| 5 | `0x0020` | `FLAGS_SOLAR_VALID` | Optional `solar_voltage_x10` field is appended |
| 6 | `0x0040` | `FLAGS_TIER_PRECISION` | Node tier: 0 = basic, 1 = precision_plus |
| 7 | `0x0080` | `FLAGS_LOW_BATTERY` | Battery voltage below low threshold |
| 8 | `0x0100` | `FLAGS_SENSOR_ERROR` | One or more sensors failed to read |
| 9–15 | — | _(reserved)_ | Must be zero |

### 4.3 Device ID in binary frames

The binary frame does **not** carry the `device_id` string (to save bytes).
When the gateway decodes a binary frame it sets `device_id` to `"unknown"`.
In LoRaWAN deployments the network server (ChirpStack) must inject the DevEUI
into the application payload context so the codec can populate the field. For
serial binary connections the operator must configure the gateway to associate
the serial port with a known device ID.

---

## 5. Legacy camelCase Format

Early firmware (pre-V1) produced a camelCase JSON payload without a
`schema_version` field. This format is still accepted by both the gateway and
the ingestor for backwards compatibility.

### 5.1 Example

```json
{
  "deviceId":       "vineguard-node-001",
  "soilMoisture":   57.2,
  "soilTempC":      18.5,
  "ambientTempC":   21.3,
  "ambientHumidity": 63.2,
  "lightLux":       245.0,
  "batteryVoltage": 3.97,
  "timestamp":      1700000000
}
```

### 5.2 Field mapping to V1

| Legacy field | V1 target | Notes |
|--------------|-----------|-------|
| `deviceId` | `device_id` | |
| `soilMoisture` | `sensors.soil_moisture_pct` | |
| `soilTempC` | `sensors.soil_temp_c` | |
| `ambientTempC` | `sensors.ambient_temp_c` | |
| `ambientHumidity` | `sensors.ambient_humidity_pct` | |
| `lightLux` | `sensors.light_lux` | |
| `batteryVoltage` | `meta.battery_voltage` | |
| `timestamp` | `timestamp` | |
| _(absent)_ | `sensors.pressure_hpa` | Always null after conversion |
| _(absent)_ | `sensors.leaf_wetness_pct` | Always null after conversion |
| _(absent)_ | `meta.battery_pct` | Always null after conversion |
| _(absent)_ | `meta.rssi` | Always null after conversion |
| _(absent)_ | `tier` | Forced to `"basic"` |

The gateway's `_decode_legacy()` function and the ingestor's `parse_payload()`
function both detect the legacy format by the presence of `deviceId` and the
absence of `schema_version`.

When the ingestor stores a legacy payload it writes `schema_version = 'legacy'`
to the `telemetry_readings` table so historical data can be identified.

---

## 6. Gateway Normalisation Rules

The gateway's `decode_auto()` function applies the following detection logic:

1. **VGPP-1 binary:** If the input is `bytes` and the first byte is `0xA1`,
   invoke `decode_binary()`. Verify CRC before any field extraction; raise
   `PayloadDecodeError` on mismatch.
2. **Text with prefix:** If the input starts with `VGPAYLOAD:`, strip the
   prefix and continue as JSON.
3. **V1 JSON:** If the parsed object contains `schema_version`, invoke
   `decode_v1_json()`. Injects `gateway_id` and substitutes `timestamp` if
   absent or zero.
4. **Compact LoRa P2P JSON:** If the parsed object contains both `v` and `id`
   keys, invoke `decode_compact_json()`. Expands abbreviated keys, injects
   `gateway_id`, synthesises `timestamp`.
5. **Legacy camelCase:** If the parsed object contains `deviceId`, invoke
   `_decode_legacy()`. Logs a debug-level warning.
6. **Unknown:** Raise `PayloadDecodeError` listing the first eight keys seen.

After decoding, `validate_v1()` performs range checks. Payloads that fail
validation are dropped with a warning log; they are not cached offline.

---

## 7. Null Handling

- **Null vs absent:** A sensor field set to `null` means the sensor hardware is
  present but the reading was unavailable (hardware error, out-of-range value,
  or a reserved field). An absent field means the sensor is not fitted to the
  node hardware at all. The gateway always emits all defined `sensors` keys,
  setting absent readings to `null`.

- **`sensor_ok` flag:** Set to `false` if **any** sensor that is expected to be
  present (based on the node's firmware configuration) failed to produce a valid
  reading. A node where soil moisture is fitted but temporarily fails returns
  `soil_moisture_pct: null` **and** `sensor_ok: false`.

- **Ingestor behaviour:** The ingestor uses Pydantic validators with `ge`/`le`
  constraints. A `null` value on a non-nullable ingestor field will cause a
  `ValidationError` and the message will be NACK'd (not stored). Ensure sensors
  that are mandatory in the schema are always populated or the firmware is
  changed to report a safe default (e.g. `0.0`).

---

## 8. Database Columns

The ingestor stores validated V1 payloads into the `telemetry_readings`
hypertable in TimescaleDB. The mapping from V1 fields to database columns is:

| DB column | Source V1 field | Type | Notes |
|-----------|-----------------|------|-------|
| `id` | _(generated)_ | `UUID` | `gen_random_uuid()` |
| `device_id` | `device_id` | `VARCHAR(64)` | FK to `nodes.device_id` (soft) |
| `node_id` | _(looked up from `nodes` table)_ | `UUID` | `NULL` if device not registered |
| `soil_moisture` | `sensors.soil_moisture_pct` | `DOUBLE PRECISION` | Required by ingestor schema |
| `soil_temp_c` | `sensors.soil_temp_c` | `DOUBLE PRECISION` | Required by ingestor schema |
| `ambient_temp_c` | `sensors.ambient_temp_c` | `DOUBLE PRECISION` | Required by ingestor schema |
| `ambient_humidity` | `sensors.ambient_humidity_pct` | `DOUBLE PRECISION` | Required by ingestor schema |
| `light_lux` | `sensors.light_lux` | `DOUBLE PRECISION` | Required by ingestor schema |
| `battery_voltage` | `meta.battery_voltage` | `DOUBLE PRECISION` | Required by ingestor schema |
| `battery_pct` | `meta.battery_pct` | _(not persisted in MVP)_ | Available in MQTT payload; not yet written to DB |
| `leaf_wetness_pct` | `sensors.leaf_wetness_pct` | `DOUBLE PRECISION` | Nullable; precision_plus only |
| `pressure_hpa` | `sensors.pressure_hpa` | `DOUBLE PRECISION` | Nullable |
| `schema_version` | `schema_version` | `VARCHAR(8)` | `"1.0"` or `"legacy"` |
| `recorded_at` | `timestamp` | `TIMESTAMPTZ` | Hypertable partition key; defaults to `now()` if absent |

The `rssi` value from `meta.rssi` is returned from `parse_payload()` in the
ingestor's normalised dict but is **not** currently written to
`telemetry_readings`. The `nodes` table has an `rssi_last` column that is
updated by the ingestor as a node health metric.

---

## Appendix: Schema Change Policy

- Additive changes (new optional fields) may be made with a minor version bump
  in the comment header only; `schema_version` stays `"1.0"`.
- Breaking changes (removed fields, changed types, changed semantics) require
  incrementing `schema_version` and updating this document, the ingestor
  schemas, and the gateway decoder simultaneously.
- The `firmware/esp32-node/include/payload_schema.h` and this document are the
  two sources of truth for the binary frame. Keep them in sync.
