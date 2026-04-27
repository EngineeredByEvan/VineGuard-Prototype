from pathlib import Path

from vineguard_gateway.lora import LoRaMessage, OfflineCache


def test_cache_append_and_drain(tmp_path: Path):
    cache = OfflineCache(tmp_path / "cache.jsonl")
    cache.append(LoRaMessage(payload={"device_id": "vg-node-001"}))
    drained = cache.drain()
    assert len(drained) == 1
    assert drained[0].payload["device_id"] == "vg-node-001"
    assert cache.drain() == []
