# VineGuard Node Field Installation Checklist

Use this checklist for every node installation. Check off each item before moving to the next section.

---

## A — Bench Test (Before Leaving the Shop)

- [ ] **Flash firmware** — `./tools/flash_device.sh --serial <SN> --env lora_p2p` (or `debug_serial` for bench only)
- [ ] **Serial smoke test** — `python tools/serial_smoke_test.py --port /dev/ttyUSB0` — all checks pass
- [ ] **All sensors present in log** — verify boot log shows `soil=OK bme=OK lux=OK` (or MISS if sensor not yet connected — expected in bare-board bench)
- [ ] **Mock mode sensor values** — in `debug_serial` env, confirm `VGPAYLOAD:` lines appear every 15 s with realistic numbers
- [ ] **Battery voltage reads correctly** — serial log shows `V=xx.xV pct=xx%` within expected range for your pack
- [ ] **LoRa radio init OK** — log shows `SX1262 init OK 915.0 MHz SF9 BW125kHz`
- [ ] **Gateway receives payload** — start gateway in `serial_json` mode (`LORA_MODE=serial_json`), confirm `Decoded serial_json payload from <device_id>` appears
- [ ] **Failsafe queue empty on fresh node** — log shows `Queue ready, depth=0`

---

## B — Node Identity and Labeling

- [ ] **Label inside lid** — printed label shows: Serial number, DeviceID, DevEUI, installed date
- [ ] **Label is legible and adhesive** — use polyester or outdoor-rated label stock
- [ ] **DevEUI matches manifest** — compare label to `provisioning_manifest.csv`
- [ ] **Photograph label** before sealing enclosure

---

## C — Cloud Registration

- [ ] **device_id registered in database** — confirm node appears in VineGuard dashboard (`/api/v1/nodes`)
- [ ] **vineyard_id and block_id correct in NVS** — serial log shows `id=<device_id> vy=<vineyard_id> blk=<block_id>` on boot
- [ ] **Node assigned to correct block** — dashboard block view shows this device_id
- [ ] **Tier set correctly** — `basic` or `precision_plus` matches hardware

---

## D — Site Selection

- [ ] **Post/wire height** — mount enclosure at 1–3 ft (30–90 cm) above ground on vine post or T-post
- [ ] **Enclosure orientation** — face enclosure away from direct afternoon sun; use shade side of post
- [ ] **LoRa line-of-sight** — confirm clear line to gateway (no dense foliage, structures, or terrain blocking direct path)
- [ ] **Distance to gateway** — measured or estimated, confirm within expected range (< 2 km open field, < 500 m dense vineyard)
- [ ] **No RF interference** — avoid mounting near irrigation control boxes or metal structures that may attenuate signal

---

## E — Enclosure Mounting

- [ ] **Enclosure secured to post** — use stainless steel hose clamps or dedicated mounting brackets
- [ ] **All cable glands face downward** — prevents water tracking into glands
- [ ] **Unused gland ports sealed** — use gland blanking plugs on any unused holes
- [ ] **Lid seal inspected** — gasket seated evenly; no pinched sensor cables
- [ ] **Lid screws finger-tight** — do not over-torque plastic enclosures

---

## F — Soil Probe Installation

- [ ] **Location chosen** — mid-row, representative of block soil type, away from drip emitter (30 cm offset)
- [ ] **Probe depth** — insert at 4–6 inch (10–15 cm) depth in root zone
- [ ] **Probe fully inserted** — no air gap between probe body and soil
- [ ] **Cable secured** — cable ties to vine wire or post to prevent pulling on probe
- [ ] **Initial reading plausible** — serial log shows `soil=XX.X%`, not stuck at 0 or 100%
- [ ] **Calibration noted** — record `dry ADC` and `wet ADC` values in provisioning notes if field-calibrating

---

## G — BME280 Radiation Shield

- [ ] **Shield mounted** — on separate short arm or bracket, 15–30 cm from main enclosure
- [ ] **Shield shaded from direct sun** — use north-facing side of post or under vine wire
- [ ] **Cable through gland** — 4-core cable (VCC, GND, SDA, SCL) routed through dedicated gland
- [ ] **Connector secure** — pull-test cable gland; no movement
- [ ] **Temperature sanity check** — serial log shows `T=XX.X°C RH=XX.X%`, temperature within ±2°C of local reference thermometer
- [ ] **Pressure plausible** — 980–1030 hPa at sea level; lower at elevation (approx. −12 hPa per 100 m)

---

## H — Lux Sensor Placement

- [ ] **Sensor mounted** — on 1–2 m cable extension, placed under canopy row or at vine height
- [ ] **Sensor pointing upward** — sensor window faces up into the canopy
- [ ] **Cable secured** — cable tied to vine wire; no slack that could catch wind
- [ ] **Lux reading plausible** — on a sunny mid-day, under-canopy reading is 5–40% of open-sky value
- [ ] **Dashboard block reference_lux_peak set** — confirm block's `reference_lux_peak` is configured (used by canopy lux analytics rule)

---

## I — Leaf Wetness Sensor (Precision+ Only)

- [ ] **Sensor clipped/attached** — on representative leaf surface or canopy position within the block
- [ ] **RS485 cable routed** — through dedicated gland, drain wire grounded at one end only
- [ ] **120 Ω termination installed** — if RS485 cable > 1 m, terminator across A–B at sensor end
- [ ] **Modbus read confirmed** — serial log shows `LEAFWET: Found at Modbus addr 1, raw=XXXX`
- [ ] **Wet/dry threshold verified** — wet test: spray sensor with water, confirm `leafWetnessPercent > 30` within 30 s
- [ ] **Dry threshold verified** — after drying, confirm reading drops below 30%

---

## J — Solar Panel and Power System

- [ ] **Panel orientation** — facing south (northern hemisphere), tilt 30–45°, no shading at noon
- [ ] **Panel secured** — mounted to post or dedicated bracket; tilt angle fixed
- [ ] **Charge controller wired correctly** — panel → controller → battery → buck converter
- [ ] **Fuse installed** — 3 A fuse in positive battery lead between battery and node
- [ ] **Battery voltage at install** — serial log shows `V > 11.0 V` (above low threshold 9.5 V)
- [ ] **Solar voltage present** — on a sunny day, `solarVoltage > 12 V` in log (if ENABLE_SOLAR_ADC=1)
- [ ] **Buck converter output** — 5.0 ± 0.1 V measured with multimeter

---

## K — First Telemetry Verification

- [ ] **USB serial check** — if accessible, confirm `VGPAYLOAD:` lines emitting
- [ ] **Gateway log** — gateway shows `Published: topic=vineguard/telemetry device=<device_id>`
- [ ] **Dashboard device online** — node status changes from `inactive` to `active` within 30 min
- [ ] **Dashboard soil moisture** — shows correct approximate value, not null
- [ ] **Dashboard temperature** — shows ambient temperature, within ±3°C of expected
- [ ] **Dashboard battery** — shows battery voltage and percent
- [ ] **No active alerts on fresh install** — unless moisture is already critically low

---

## L — Post-Install Documentation

Record the following in the installation log (spreadsheet or paper form):

| Field | Value |
|-------|-------|
| Install date | |
| Installer name | |
| Node serial | |
| GPS coordinates | |
| Post location | (row number, vine number) |
| Soil probe depth (cm) | |
| Lux sensor height (cm) | |
| Leaf wetness position | (leaf position, height) |
| Battery voltage at install | |
| Notes | |

Photograph: enclosure mounted, soil probe installed, BME280 shield, lux sensor, solar panel.
