# VineGuard ESP32 Node Firmware (MVP)

## Build modes
- `heltec_debug`: serial-only, mock sensors, no deep sleep.
- `heltec_lora_p2p`: sensor reads + LoRa P2P uplink interface.
- `heltec_lorawan`: OTAA interface scaffold (RadioLib integration TODO).

## Quick start
```bash
cd firmware/esp32-node
pio run -e heltec_debug
pio run -e heltec_debug -t upload
pio device monitor -b 115200
```

## Provisioning
1. Copy `tools/provisioning_manifest.example.csv` to `tools/provisioning_manifest.csv`.
2. Fill serial + LoRaWAN keys.
3. Run `tools/flash_device.sh <SERIAL>` (or `.ps1` on Windows).

`make_keys_header.py` validates hex lengths and writes `include/lorawan_keys.h` (gitignored).

## Sensor wiring summary
- Soil SEN0308 analog -> `PIN_SOIL_ADC`
- BME280 I2C -> `PIN_I2C_SDA/SCL`
- Lux sensor (BH1750-compatible/SEN0390 adapter) -> I2C same bus
- Battery divider -> `PIN_BATTERY_ADC`
- Optional solar divider -> `PIN_SOLAR_ADC`
- Optional leaf wetness RS485 -> UART pins in `pins.h`

## Power lifecycle
- Sensor rail enabled before sample, disabled after transmit.
- Deep sleep interval uses `sampleIntervalSec` from NVS.
- Low battery doubles/quadruples sleep interval.

## Limitations
- LoRa P2P + LoRaWAN radio transmission classes are safe stubs pending board-specific RadioLib register tuning.
- Leaf wetness RS485 map is placeholder; protocol-specific commands required.
- OTA is intentionally disabled by default for LoRa-only deployments.
