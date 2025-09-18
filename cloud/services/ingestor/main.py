import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from paho.mqtt import client as mqtt_client
from pydantic import BaseModel, BaseSettings, Field, ValidationError
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestor")


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    mqtt_host: str = Field(..., env="MQTT_HOST")
    mqtt_port: int = Field(1883, env="MQTT_PORT")
    mqtt_username: Optional[str] = Field(None, env="MQTT_USERNAME")
    mqtt_password: Optional[str] = Field(None, env="MQTT_PASSWORD")
    mqtt_telemetry_topic: str = Field("org/+/nodes/+/telemetry", env="MQTT_TELEMETRY_TOPIC")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class TelemetryPayload(BaseModel):
    org_id: UUID
    node_id: UUID
    timestamp: datetime
    battery_level: Optional[float]
    temperature: Optional[float]
    moisture: Optional[float]
    payload: dict = Field(default_factory=dict)


class Ingestor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings.database_url, pool_pre_ping=True)
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.node_cache: dict[UUID, UUID] = {}
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self) -> None:
        logger.info("Connecting to MQTT broker %s:%s", self.settings.mqtt_host, self.settings.mqtt_port)
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port)
        thread = threading.Thread(target=self.client.loop_forever, daemon=True)
        thread.start()
        thread.join()

    def on_connect(self, client: mqtt_client.Client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Connected to MQTT. Subscribing to %s", self.settings.mqtt_telemetry_topic)
            client.subscribe(self.settings.mqtt_telemetry_topic)
        else:
            logger.error("Failed to connect to MQTT: %s", rc)

    def on_message(self, client: mqtt_client.Client, userdata, msg):
        try:
            raw = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.exception("Invalid JSON received on topic %s", msg.topic)
            return

        topic_parts = msg.topic.split("/")
        org_id = raw.get("org_id") or (topic_parts[1] if len(topic_parts) > 1 else None)
        node_id = raw.get("node_id") or (topic_parts[3] if len(topic_parts) > 3 else None)
        if org_id is None or node_id is None:
            logger.warning("Telemetry missing org or node id: %s", raw)
            return

        original = raw.copy()
        timestamp = raw.get("timestamp") or raw.get("reading_time") or datetime.now(timezone.utc).isoformat()
        envelope = {
            "org_id": org_id,
            "node_id": node_id,
            "timestamp": timestamp,
            "battery_level": raw.get("battery_level"),
            "temperature": raw.get("temperature"),
            "moisture": raw.get("moisture"),
            "payload": original,
        }

        try:
            payload = TelemetryPayload(**envelope)
        except ValidationError:
            logger.exception("Telemetry validation failed: %s", raw)
            return

        self.persist(payload)

    def persist(self, payload: TelemetryPayload) -> None:
        node_org = self.get_node_org(payload.node_id)
        if node_org is None:
            logger.warning("Node %s not registered; skipping", payload.node_id)
            return
        if str(node_org) != str(payload.org_id):
            logger.warning("Org mismatch for node %s", payload.node_id)
            return

        with Session(self.engine) as session:
            session.execute(
                text(
                    """
                    INSERT INTO telemetry_raw (org_id, node_id, reading_time, payload)
                    VALUES (:org_id, :node_id, :reading_time, :payload)
                    """
                ),
                {
                    "org_id": str(payload.org_id),
                    "node_id": str(payload.node_id),
                    "reading_time": payload.timestamp,
                    "payload": json.dumps(payload.payload),
                },
            )

            session.execute(
                text(
                    """
                    INSERT INTO node_status (node_id, last_seen, battery_level, temperature, moisture, updated_at)
                    VALUES (:node_id, :last_seen, :battery_level, :temperature, :moisture, NOW())
                    ON CONFLICT (node_id) DO UPDATE SET
                        last_seen = EXCLUDED.last_seen,
                        battery_level = EXCLUDED.battery_level,
                        temperature = EXCLUDED.temperature,
                        moisture = EXCLUDED.moisture,
                        updated_at = NOW()
                    """
                ),
                {
                    "node_id": str(payload.node_id),
                    "last_seen": payload.timestamp,
                    "battery_level": payload.battery_level,
                    "temperature": payload.temperature,
                    "moisture": payload.moisture,
                },
            )

            session.commit()

        event = {
            "event": "telemetry",
            "org_id": str(payload.org_id),
            "node_id": str(payload.node_id),
            "timestamp": payload.timestamp.isoformat(),
            "battery_level": payload.battery_level,
            "temperature": payload.temperature,
            "moisture": payload.moisture,
        }
        self.redis.publish(f"org:{payload.org_id}:live", json.dumps(event, default=str))

    def get_node_org(self, node_id: UUID) -> Optional[UUID]:
        cached = self.node_cache.get(node_id)
        if cached:
            return cached
        with Session(self.engine) as session:
            record = session.execute(
                text("SELECT org_id FROM nodes WHERE id = :node_id"),
                {"node_id": str(node_id)},
            ).mappings().first()
            if record:
                self.node_cache[node_id] = UUID(record["org_id"])
                return self.node_cache[node_id]
        return None


def main() -> None:
    settings = Settings()
    ingestor = Ingestor(settings)
    ingestor.start()


if __name__ == "__main__":
    main()
