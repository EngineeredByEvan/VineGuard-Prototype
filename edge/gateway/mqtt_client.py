from __future__ import annotations

"""MQTT client abstraction for the gateway."""

import logging
import threading
from typing import Callable, List

import paho.mqtt.client as mqtt

from .config import Config


class CloudMqttClient:
    """Wraps paho-mqtt to provide connection tracking and callbacks."""

    def __init__(
        self,
        config: Config,
        on_message: Callable[[str, bytes], None],
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._client = mqtt.Client(client_id=config.gateway_id, clean_session=False)
        if config.mqtt_username:
            self._client.username_pw_set(config.mqtt_username, config.mqtt_password)
        if config.mqtt_use_tls:
            self._client.tls_set(
                ca_certs=str(config.mqtt_ca_cert) if config.mqtt_ca_cert else None,
                certfile=str(config.mqtt_client_cert) if config.mqtt_client_cert else None,
                keyfile=str(config.mqtt_client_key) if config.mqtt_client_key else None,
            )
            if config.mqtt_tls_insecure:
                self._client.tls_insecure_set(True)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self._client.reconnect_delay_set(min_delay=config.backoff_base, max_delay=config.backoff_max)
        self._connected = threading.Event()
        self._connection_listeners: List[Callable[[bool], None]] = []
        self._logger = logging.getLogger("gateway.mqtt")
        self._lock = threading.Lock()

    def start(self) -> None:
        self._logger.info(
            "Connecting to MQTT broker",
            extra={"host": self._config.mqtt_host, "port": self._config.mqtt_port, "tls": self._config.mqtt_use_tls},
        )
        self._client.loop_start()
        try:
            self._client.connect(self._config.mqtt_host, self._config.mqtt_port, keepalive=60)
        except Exception:
            self._logger.exception("Initial MQTT connection failed")

    def stop(self) -> None:
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:
            self._logger.exception("Error while disconnecting MQTT client")

    def publish(self, topic: str, payload: str, qos: int = 1) -> bool:
        with self._lock:
            if not self.is_connected:
                return False
            try:
                result = self._client.publish(topic, payload=payload, qos=qos)
            except Exception:
                self._logger.exception("MQTT publish failed", extra={"topic": topic})
                return False
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self._logger.warning("MQTT publish returned error", extra={"topic": topic, "rc": result.rc})
            return False
        return True

    def subscribe(self, topic: str, qos: int = 1) -> None:
        try:
            result, _ = self._client.subscribe(topic, qos=qos)
        except Exception:
            self._logger.exception("Failed to subscribe to topic", extra={"topic": topic})
            return
        if result == mqtt.MQTT_ERR_SUCCESS:
            self._logger.info("Subscribed to topic", extra={"topic": topic})
        else:
            self._logger.warning("Subscription deferred", extra={"topic": topic, "rc": result})

    def add_connection_listener(self, callback: Callable[[bool], None]) -> None:
        self._connection_listeners.append(callback)

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def _handle_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:  # type: ignore[override]
        success = rc == 0
        if success:
            self._connected.set()
            self._logger.info("Connected to MQTT broker")
        else:
            self._logger.error("MQTT connection failed", extra={"rc": rc})
        for callback in self._connection_listeners:
            try:
                callback(success)
            except Exception:
                self._logger.exception("Connection listener failed")

    def _handle_disconnect(self, client: mqtt.Client, userdata, rc) -> None:  # type: ignore[override]
        self._connected.clear()
        self._logger.warning("Disconnected from MQTT broker", extra={"rc": rc})
        for callback in self._connection_listeners:
            try:
                callback(False)
            except Exception:
                self._logger.exception("Connection listener failed")

    def _handle_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:  # type: ignore[override]
        try:
            self._on_message(message.topic, message.payload)
        except Exception:
            self._logger.exception("Failed to handle MQTT message", extra={"topic": message.topic})


__all__ = ["CloudMqttClient"]
