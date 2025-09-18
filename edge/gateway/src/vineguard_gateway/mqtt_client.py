from __future__ import annotations

import json
import ssl
from typing import Iterable

import paho.mqtt.client as mqtt
from loguru import logger

from .config import GatewaySettings
from .lora import LoRaMessage


class MqttPublisher:
    def __init__(self, settings: GatewaySettings) -> None:
        self.settings = settings
        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.tls_set(
            ca_certs=str(settings.ca_cert_path),
            certfile=str(settings.client_cert_path) if settings.client_cert_path else None,
            keyfile=str(settings.client_key_path) if settings.client_key_path else None,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        self.client.tls_insecure_set(False)

    def connect(self) -> None:
        logger.info("Connecting to MQTT {}:{}", self.settings.mqtt_host, self.settings.mqtt_port)
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        self.client.loop_start()

    def publish_messages(self, messages: Iterable[LoRaMessage]) -> None:
        for message in messages:
            payload = json.dumps(message.payload)
            result = self.client.publish(self.settings.mqtt_topic, payload=payload, qos=1)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise ConnectionError(f"MQTT publish failed: {mqtt.error_string(result.rc)}")
            logger.info("Published telemetry from {}", message.payload.get("deviceId"))
