"""
test_gateway.py — Integration-style tests for the VineGuard gateway process.

Tests offline cache, mock LoRa interface, and the main process loop logic.
Run with: pytest edge/gateway/tests/test_gateway.py -v
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from vineguard_gateway.lora import LoRaMessage, OfflineCache, _MockLoRa


# ─── OfflineCache ─────────────────────────────────────────────────────────────

class TestOfflineCache:
    def _make_cache(self, tmp_path: Path) -> OfflineCache:
        return OfflineCache(tmp_path / "test-cache.jsonl")

    def test_append_and_drain(self, tmp_path):
        cache = self._make_cache(tmp_path)
        msg1 = LoRaMessage(payload={"device_id": "vg-001", "schema_version": "1.0",
                                    "sensors": {}, "meta": {}})
        msg2 = LoRaMessage(payload={"device_id": "vg-002", "schema_version": "1.0",
                                    "sensors": {}, "meta": {}})
        cache.append(msg1)
        cache.append(msg2)

        drained = cache.drain()
        assert len(drained) == 2
        ids = {m.payload["device_id"] for m in drained}
        assert ids == {"vg-001", "vg-002"}

    def test_drain_deletes_file(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache.append(LoRaMessage(payload={"device_id": "x", "schema_version": "1.0",
                                          "sensors": {}, "meta": {}}))
        cache.drain()
        assert not cache.path.exists()

    def test_drain_empty_returns_empty(self, tmp_path):
        cache = self._make_cache(tmp_path)
        assert cache.drain() == []

    def test_drain_skips_malformed_lines(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache.path.parent.mkdir(parents=True, exist_ok=True)
        with cache.path.open("w") as f:
            f.write('{"device_id":"good","schema_version":"1.0","sensors":{},"meta":{}}\n')
            f.write("THIS IS NOT JSON\n")
            f.write('{"device_id":"also-good","schema_version":"1.0","sensors":{},"meta":{}}\n')
        drained = cache.drain()
        assert len(drained) == 2  # malformed line skipped

    def test_append_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "cache.jsonl"
        cache = OfflineCache(deep_path)
        cache.append(LoRaMessage(payload={"device_id": "vg-001", "schema_version": "1.0",
                                          "sensors": {}, "meta": {}}))
        assert deep_path.exists()


# ─── Mock LoRa interface ──────────────────────────────────────────────────────

class TestMockLoRa:
    def _settings(self):
        s = MagicMock()
        s.lora_mode   = "mock"
        s.gateway_id  = "vg-gw-test"
        return s

    def test_yields_messages(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        msgs = lora.read_messages()
        assert len(msgs) >= 1

    def test_message_has_schema_version(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        msg = lora.read_messages()[0]
        assert msg.payload["schema_version"] == "1.0"

    def test_message_has_gateway_id(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        msg = lora.read_messages()[0]
        assert msg.payload["gateway_id"] == "vg-gw-test"

    def test_rotates_scenarios(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        ids = [lora.read_messages()[0].payload["device_id"] for _ in range(6)]
        # Should cycle through at least 2 different device IDs
        assert len(set(ids)) >= 2

    def test_has_sensors_and_meta(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        payload = lora.read_messages()[0].payload
        assert "sensors" in payload
        assert "meta" in payload
        assert payload["sensors"]["ambient_temp_c"] is not None

    def test_live_timestamp(self):
        lora = _MockLoRa(self._settings())
        lora.open()
        before = int(time.time())
        payload = lora.read_messages()[0].payload
        assert payload["timestamp"] >= before


# ─── Gateway process logic (mocked MQTT) ──────────────────────────────────────

class TestGatewayProcessLogic:
    """Test _process_messages logic without a real MQTT broker."""

    def _make_valid_payload(self, device_id="vg-node-001"):
        return {
            "schema_version": "1.0",
            "device_id": device_id,
            "tier": "basic",
            "sensors": {
                "soil_moisture_pct": 28.4,
                "ambient_temp_c": 21.3,
                "ambient_humidity_pct": 63.0,
                "pressure_hpa": 1008.0,
                "light_lux": 20000.0,
            },
            "meta": {
                "battery_voltage": 11.5,
                "battery_pct": 65,
                "sensor_ok": True,
            },
        }

    def test_valid_message_published(self, tmp_path):
        from vineguard_gateway.main import _process_messages

        publisher = MagicMock()
        publisher.settings = MagicMock()
        publisher.settings.mqtt_topic = "vineguard/telemetry"

        cache = OfflineCache(tmp_path / "cache.jsonl")
        msg   = LoRaMessage(payload=self._make_valid_payload())

        _process_messages([msg], publisher, cache)

        publisher.publish_messages.assert_called_once()
        # Cache should remain empty (publish succeeded)
        assert cache.drain() == []

    def test_invalid_payload_dropped(self, tmp_path):
        from vineguard_gateway.main import _process_messages

        publisher = MagicMock()
        publisher.settings = MagicMock()
        publisher.settings.mqtt_topic = "vineguard/telemetry"

        cache = OfflineCache(tmp_path / "cache.jsonl")
        # device_id too short → validation fails
        bad_payload = self._make_valid_payload()
        bad_payload["device_id"] = "ab"
        msg = LoRaMessage(payload=bad_payload)

        _process_messages([msg], publisher, cache)

        publisher.publish_messages.assert_not_called()

    def test_failed_publish_goes_to_cache(self, tmp_path):
        from vineguard_gateway.main import _process_messages

        publisher = MagicMock()
        publisher.settings = MagicMock()
        publisher.settings.mqtt_topic = "vineguard/telemetry"
        publisher.publish_messages.side_effect = ConnectionError("broker down")

        cache = OfflineCache(tmp_path / "cache.jsonl")
        msg   = LoRaMessage(payload=self._make_valid_payload())

        with patch("vineguard_gateway.main._publish_with_retry", side_effect=ConnectionError("broker down")):
            _process_messages([msg], publisher, cache)

        drained = cache.drain()
        assert len(drained) == 1
        assert drained[0].payload["device_id"] == "vg-node-001"

    def test_empty_message_list_no_publish(self, tmp_path):
        from vineguard_gateway.main import _process_messages

        publisher = MagicMock()
        publisher.settings = MagicMock()
        publisher.settings.mqtt_topic = "vineguard/telemetry"
        cache = OfflineCache(tmp_path / "cache.jsonl")

        _process_messages([], publisher, cache)
        publisher.publish_messages.assert_not_called()
