from unittest.mock import Mock

from vineguard_gateway.lora import LoRaMessage
from vineguard_gateway.mqtt_client import MqttPublisher


class FakeSettings:
    mqtt_username = ""
    mqtt_password = ""
    ca_cert_path = None
    client_cert_path = None
    client_key_path = None
    mqtt_host = "localhost"
    mqtt_port = 1883
    mqtt_topic = "vineguard/telemetry"


def test_publish_messages_success(monkeypatch):
    pub = MqttPublisher(FakeSettings())
    pub.client = Mock()
    pub.client.publish.return_value = type("R", (), {"rc": 0})()
    pub.publish_messages([LoRaMessage(payload={"device_id": "vg-node-001"})])
    assert pub.client.publish.called
