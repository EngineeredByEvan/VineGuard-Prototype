#pragma once
// lorawan_keys.example.h — LoRaWAN OTAA key template
//
// INSTRUCTIONS:
//  1. Copy this file to lorawan_keys.h in the same directory.
//  2. Fill in real keys from your LoRaWAN network server.
//  3. lorawan_keys.h is listed in .gitignore and will NEVER be committed.
//
// Use tools/make_keys_header.py to auto-generate lorawan_keys.h from
// your provisioning_manifest.csv (recommended for batch provisioning).
//
// See docs/PROVISIONING.md for full instructions.

// DevEUI — 8-byte unique device identifier (hex, MSB first)
// Example: printed on Heltec V3 module as "DevEUI: A8 40 41 ..."
#define LORAWAN_DEV_EUI  { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

// AppEUI / JoinEUI — 8-byte application identifier (hex, MSB first)
// Get this from your LoRaWAN server (TTN, ChirpStack, Helium, etc.)
#define LORAWAN_APP_EUI  { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

// AppKey — 16-byte root encryption key (hex, MSB first)
// KEEP THIS SECRET.  Never log or print this key.
#define LORAWAN_APP_KEY  { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, \
                           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

// NwkKey — 16-byte network root key (LoRaWAN 1.1)
// For LoRaWAN 1.0 servers set this equal to LORAWAN_APP_KEY.
#define LORAWAN_NWK_KEY  { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, \
                           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

// Human-readable device ID that maps to the device in the VineGuard dashboard.
// Must match the device_id registered in the cloud database.
#define DEVICE_ID        "vineguard-node-000"
#define NODE_SERIAL      "VG-000000"
#define VINEYARD_ID      "unset"
#define BLOCK_ID         "unset"
#define NODE_TYPE        "basic"
