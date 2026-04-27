# VineGuard Node Provisioning Guide

**Last updated:** 2026-04-27  
**Applies to:** firmware v0.1.x, provisioning tooling in `firmware/esp32-node/tools/`

---

## 1. Overview

Provisioning is the process of assigning a unique identity and cryptographic
keys to each VineGuard node before it is deployed in the field. This guide
covers batch provisioning for deployments of 1–50 nodes using the tooling in
`firmware/esp32-node/tools/`.

The high-level flow is:

```
1. Create / update provisioning_manifest.csv with one row per node
2. For each node:
   a. Run make_keys_header.py  →  generates include/lorawan_keys.h
   b. Run flash_device script  →  builds firmware and uploads to the node
   c. Print and attach device label
3. Register each device_id in the VineGuard cloud database
```

This guide uses `lora_p2p` as the default PlatformIO environment. Substitute
`lorawan_otaa` for LoRaWAN OTAA deployments where a LoRaWAN network server is
available.

---

## 2. LoRaWAN Key Concepts

Understanding these three identifiers is essential. Confusing them is a common
source of provisioning failures.

| Identifier | Length | Where to find it | Description |
|-----------|--------|-----------------|-------------|
| **DevEUI** | 8 bytes (16 hex chars) | Printed on the Heltec V3 module label as `DevEUI: AA BB CC ...`; also readable from the network server device list | Globally unique hardware identifier for the radio module. Think of it as a MAC address. |
| **AppEUI / JoinEUI** | 8 bytes (16 hex chars) | Assigned by your LoRaWAN network server (TTN, ChirpStack, Helium, etc.) when you create an Application | Application-scope identifier. All nodes in the same application share the same AppEUI. |
| **AppKey** | 16 bytes (32 hex chars) | Generated during device registration on the network server, or generated offline and then imported | Root encryption key used to derive session keys during OTAA join. **Must be kept secret.** |
| **NwkKey** | 16 bytes (32 hex chars) | Same source as AppKey | LoRaWAN 1.1 network root key. For LoRaWAN 1.0 network servers (most ChirpStack deployments), set this equal to AppKey. |

> **Security note:** AppKey and NwkKey are the master secrets for a node. If
> they are compromised, an attacker can impersonate the node or decrypt all its
> traffic. See §10 for security requirements.

---

## 3. Provisioning Manifest CSV

All node identity and key data lives in a single CSV file:

```
firmware/esp32-node/tools/provisioning_manifest.csv
```

This file is in `.gitignore` because it contains AppKeys. The example template
at `provisioning_manifest.example.csv` shows the format.

### 3.1 Columns

| Column | Required | Format | Description |
|--------|----------|--------|-------------|
| `serial` | Yes | `VG-NNNNNN` | Human-assigned serial number; printed on the device label |
| `device_id` | Yes | 4–64 chars `[a-zA-Z0-9_-]` | Logical ID in the VineGuard cloud; must match `nodes.device_id` in the database |
| `dev_eui` | Yes | 16 hex chars, no separators | DevEUI from the Heltec module or network server |
| `app_eui` | Yes | 16 hex chars, no separators | AppEUI / JoinEUI from the network server Application |
| `app_key` | Yes | 32 hex chars, no separators | AppKey (root encryption key) |
| `nwk_key` | Yes | 32 hex chars, no separators | NwkKey; for LoRaWAN 1.0 servers copy the `app_key` value |
| `node_type` | Yes | `basic` or `precision_plus` | Controls which sensors are enabled in the firmware build |
| `vineyard_id` | Yes | string | Must match `vineyards.id` or a slug used by seed scripts |
| `block_id` | Yes | string | Must match `blocks.id` or a slug used by seed scripts |
| `notes` | No | string | Free-text notes; not used by tooling |

### 3.2 How to obtain the DevEUI

- **From the module:** The Heltec WiFi LoRa 32 V3 prints the DevEUI on a sticker
  on the top of the module (format: `AA:BB:CC:DD:EE:FF:00:11`). Remove colons
  and convert to uppercase for the CSV.
- **From the network server:** After registering the device, the network server
  confirms the DevEUI. Some servers auto-generate one if you do not supply one
  (not recommended — use the hardware-printed EUI for traceability).

### 3.3 Example rows

```csv
serial,device_id,dev_eui,app_eui,app_key,nwk_key,node_type,vineyard_id,block_id,notes
VG-000001,vg-node-001,AABBCCDDEEFF0011,0000000000000001,00112233445566778899AABBCCDDEEFF,00112233445566778899AABBCCDDEEFF,basic,vy-copper-creek,blk-cabernet,South-west corner post
VG-000002,vg-node-002,AABBCCDDEEFF0022,0000000000000001,00112233445566778899AABBCCDDEEF0,00112233445566778899AABBCCDDEEF0,basic,vy-copper-creek,blk-cabernet,Row 12 mid-block
VG-000003,vg-node-003,AABBCCDDEEFF0033,0000000000000001,00112233445566778899AABBCCDDEEA1,00112233445566778899AABBCCDDEEA1,precision_plus,vy-copper-creek,blk-pinot,Pinot block NW corner
```

---

## 4. make_keys_header.py

This script reads one row from the provisioning manifest and generates the
`include/lorawan_keys.h` header that the firmware includes at compile time.

### 4.1 Location

```
firmware/esp32-node/tools/make_keys_header.py
```

### 4.2 Usage

```bash
# Typical usage — generate keys for serial VG-000001
python3 tools/make_keys_header.py --serial VG-000001

# Specify a non-default manifest path
python3 tools/make_keys_header.py --serial VG-000001 --manifest /path/to/manifest.csv

# Show AppKey value in terminal output (DANGER: bench use only, see warning below)
python3 tools/make_keys_header.py --serial VG-000001 --show-secrets
```

### 4.3 What it generates

The script writes `firmware/esp32-node/include/lorawan_keys.h`, for example:

```c
#pragma once
// lorawan_keys.h — AUTO-GENERATED by tools/make_keys_header.py
// DO NOT COMMIT THIS FILE.  It is listed in .gitignore.
// Node serial: VG-000001

#define LORAWAN_DEV_EUI  { 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11 }
#define LORAWAN_APP_EUI  { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01 }
#define LORAWAN_APP_KEY  { 0x00, 0x11, 0x22, ... }
#define LORAWAN_NWK_KEY  { 0x00, 0x11, 0x22, ... }

#define DEVICE_ID        "vg-node-001"
#define NODE_SERIAL      "VG-000001"
#define VINEYARD_ID      "vy-copper-creek"
#define BLOCK_ID         "blk-cabernet"
#define NODE_TYPE        "basic"
```

This file is consumed by `config.h` and the LoRaWAN radio drivers.

### 4.4 --show-secrets warning

By default the script prints only the DevEUI and DeviceID to stdout. AppKey
and NwkKey values are **never** written to stdout unless `--show-secrets` is
passed. Use `--show-secrets` only on a secure bench workstation, never in a
CI pipeline or shared terminal session.

### 4.5 Output path

The file is always written to `firmware/esp32-node/include/lorawan_keys.h`.
This path is listed in `.gitignore`. If you customise the output path with
`--output`, ensure the destination is also excluded from version control.

---

## 5. Windows PowerShell Flash Flow

Prerequisites: Python 3 in PATH, PlatformIO Core (`pio`) in PATH.

```powershell
# From the firmware/esp32-node directory:
.\tools\flash_device.ps1 -Serial VG-000001 -Env lora_p2p

# With a specific COM port:
.\tools\flash_device.ps1 -Serial VG-000001 -Env lora_p2p -Port COM3

# With a custom manifest location:
.\tools\flash_device.ps1 -Serial VG-000001 -Env lora_p2p -Manifest C:\keys\manifest.csv
```

The script performs four steps and prints progress at each:

1. Validates the serial number exists in the manifest.
2. Generates `lorawan_keys.h` by calling `make_keys_header.py`.
3. Builds the firmware with `pio run --environment lora_p2p`.
4. Uploads with `pio run --environment lora_p2p --target upload`.
5. Prints the device label information (Serial, DeviceID, DevEUI).

If any step fails the script exits non-zero and the subsequent steps do not run.

---

## 6. Bash Flash Flow

Prerequisites: Python 3, PlatformIO Core (`pio`) in PATH.

```bash
# From the firmware/esp32-node directory:
./tools/flash_device.sh --serial VG-000001 --env lora_p2p

# With a specific serial port:
./tools/flash_device.sh --serial VG-000001 --env lora_p2p --port /dev/ttyUSB0

# With a custom manifest:
./tools/flash_device.sh --serial VG-000001 --env lora_p2p --manifest ~/keys/manifest.csv
```

The steps are identical to the PowerShell flow. On completion the script prints
the device label block to stdout.

---

## 7. Manual Flash Without Scripts

Use this approach if the flash scripts are not available or you need more
control (e.g., custom PlatformIO environment flags).

```bash
# Step 1 — generate the keys header for the target node
cd firmware/esp32-node
python3 tools/make_keys_header.py --serial VG-000001

# Step 2 — verify the header was created
ls -l include/lorawan_keys.h

# Step 3 — build and upload (lora_p2p environment shown; substitute as needed)
pio run -e lora_p2p --target upload

# Step 4 — monitor serial output to confirm boot and first payload
pio device monitor --baud 115200
# Look for lines like:
#   [INFO] Device: vg-node-001 | FW 0.1.0
#   VGPAYLOAD:{"v":"1.0","id":"vg-node-001",...}
```

Available PlatformIO environments (defined in `platformio.ini`):

| Environment | Build mode | Payload format |
|-------------|-----------|----------------|
| `debug_serial` | `DEBUG_SERIAL` | JSON to Serial only (no radio) |
| `lora_p2p` | `LORA_P2P` | Compact JSON over raw LoRa |
| `lorawan_otaa` | `LORAWAN_OTAA` | VGPP-1 binary over LoRaWAN OTAA |
| `lora_p2p_mock` | `LORA_P2P` + `MOCK_SENSORS` | Compact JSON with simulated sensor data |

---

## 8. Node Labeling

After a successful flash, print a label for each node and attach it inside the
enclosure lid (not on the outside where it may be weather-damaged).

### 8.1 Required label fields

| Field | Example | Source |
|-------|---------|--------|
| Serial | `VG-000001` | `manifest.csv` column `serial` |
| Device ID | `vg-node-001` | `manifest.csv` column `device_id` |
| DevEUI | `AABBCCDDEEFF0011` | `manifest.csv` column `dev_eui` |
| Node type | `basic` | `manifest.csv` column `node_type` |
| Vineyard / Block | `vy-copper-creek / blk-cabernet` | `manifest.csv` |

The flash scripts print this information to the terminal at the end of a
successful flash. Copy it directly to your label printer template.

### 8.2 Placement

- Primary label: inside the enclosure lid — protected from UV and moisture.
- Secondary sticker on the outside (Serial and Device ID only): visible for
  field identification without opening the enclosure.

---

## 9. Registering in VineGuard Cloud

The `device_id` embedded in the firmware must match the `device_id` registered
in the `nodes` table of the VineGuard database. If there is a mismatch the
ingestor will still store telemetry (the `node_id` foreign key will be `NULL`)
but the analytics service and dashboard will not associate the readings with the
correct vineyard block.

### 9.1 Registration methods

**Using seed_demo.py (development / demo):**

```bash
# From the cloud/tools directory:
python3 cloud/seed_demo.py
```

This script populates example vineyards, blocks, and nodes. Review and edit it
to match your real serial numbers, device_ids, and block assignments.

**Direct SQL insert (production):**

```sql
INSERT INTO nodes (block_id, device_id, name, tier, lat, lon)
VALUES (
    (SELECT id FROM blocks WHERE name = 'Cabernet Block A'),
    'vg-node-001',
    'Node 001 - SW Corner',
    'basic',
    -33.8688,
    151.2093
);
```

**Via the API (if the admin endpoint is available):**

```http
POST /api/v1/nodes
Content-Type: application/json

{
  "block_id": "...",
  "device_id": "vg-node-001",
  "name": "Node 001 - SW Corner",
  "tier": "basic"
}
```

---

## 10. Security Warnings

These are non-negotiable requirements. Violations can result in sensor data
being spoofed or encrypted comms being decrypted by third parties.

1. **Never commit `lorawan_keys.h`.**  
   The file is in `.gitignore`. If it ever appears in `git status` as an
   untracked file you want to add, stop and investigate. Running
   `git rm --cached firmware/esp32-node/include/lorawan_keys.h` will remove it
   from a future commit if it was accidentally staged.

2. **Never commit `provisioning_manifest.csv`.**  
   This file is also in `.gitignore`. Store it in a password manager, encrypted
   volume, or secrets management system (e.g., HashiCorp Vault, AWS Secrets
   Manager).

3. **Never log or print the AppKey in production.**  
   The `--show-secrets` flag is for bench work only. Ensure CI pipelines do not
   use it. Application logs should never contain key material.

4. **Use publish-only MQTT credentials for the gateway.**  
   The gateway's MQTT user (`gateway_publisher` by default) should have write
   permission only on `vineguard/telemetry`. It must not have subscribe or admin
   rights. Configure this in the Mosquitto ACL file or your cloud broker's IAM.

5. **Rotate keys if compromised.**  
   If an AppKey is leaked:
   - Generate new AppKey and NwkKey values.
   - Update the provisioning manifest.
   - Re-flash the affected node(s) using the flash scripts.
   - Re-register the new keys in the LoRaWAN network server.
   - Old sessions are invalidated on the next rejoin.

6. **Physical security.**  
   The Heltec module prints the DevEUI on its label. If a node is stolen, an
   attacker learns the DevEUI but not the AppKey. Deregister stolen nodes from
   the network server immediately.
