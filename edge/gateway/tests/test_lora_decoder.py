from vineguard_gateway.lora import decode_binary_payload, normalize_for_ingestor


def test_normalize_legacy_passthrough():
    p = {
        "deviceId": "vineguard-node-001",
        "soilMoisture": 25,
        "soilTempC": 18,
        "ambientTempC": 21,
        "ambientHumidity": 63,
        "lightLux": 245,
        "batteryVoltage": 3.9,
    }
    out = normalize_for_ingestor(p)
    assert out["deviceId"] == "vineguard-node-001"


def test_decode_binary_success():
    import struct

    data = struct.pack(">B H h h H H H B B", 1, 7, 250, 213, 631, 245, 3970, 0, 1)
    crc = sum(data[:15]) & 0xFFFF
    packet = data + struct.pack(">H", crc)
    payload = decode_binary_payload(packet)
    assert payload["schema_version"] == "1.0"
    assert payload["sensors"]["soil_moisture_pct"] == 25.0
