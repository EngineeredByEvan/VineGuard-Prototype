import json
import logging
import random
import time
from datetime import datetime, timezone
from uuid import UUID, uuid5

from passlib.context import CryptContext
from paho.mqtt import publish
from pydantic import BaseSettings, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    mqtt_host: str = Field(..., env="MQTT_HOST")
    mqtt_port: int = Field(1883, env="MQTT_PORT")
    mqtt_username: str | None = Field(None, env="MQTT_USERNAME")
    mqtt_password: str | None = Field(None, env="MQTT_PASSWORD")
    demo_email: str = Field("demo@vineguard.io", env="DEMO_EMAIL")
    demo_password: str = Field("demo1234", env="DEMO_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class SeedContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings.database_url, pool_pre_ping=True)
        self.org_id = uuid5(NAMESPACE, "vineguard-org")
        self.site_id = uuid5(NAMESPACE, "vineguard-site")
        self.node_id = uuid5(NAMESPACE, "vineguard-node")

    def seed(self) -> None:
        with Session(self.engine) as session:
            session.execute(
                text(
                    """
                    INSERT INTO orgs (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": str(self.org_id), "name": "VineGuard Demo"},
            )
            session.execute(
                text(
                    """
                    INSERT INTO sites (id, org_id, name, location)
                    VALUES (:id, :org_id, :name, :location)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": str(self.site_id),
                    "org_id": str(self.org_id),
                    "name": "Demo Vineyard",
                    "location": "Field 12",
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO nodes (id, org_id, site_id, name, hardware_id)
                    VALUES (:id, :org_id, :site_id, :name, :hardware_id)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": str(self.node_id),
                    "org_id": str(self.org_id),
                    "site_id": str(self.site_id),
                    "name": "Soil Sensor A",
                    "hardware_id": "vineguard-demo-001",
                },
            )

            user_exists = session.execute(
                text("SELECT 1 FROM users WHERE email = :email"),
                {"email": self.settings.demo_email},
            ).first()
            if not user_exists:
                session.execute(
                    text(
                        """
                        INSERT INTO users (id, org_id, email, password_hash, role)
                        VALUES (:id, :org_id, :email, :password_hash, 'admin')
                        """
                    ),
                    {
                        "id": str(uuid5(NAMESPACE, "demo-user")),
                        "org_id": str(self.org_id),
                        "email": self.settings.demo_email,
                        "password_hash": PWD_CONTEXT.hash(self.settings.demo_password),
                    },
                )
            session.commit()
        logger.info("Seeded demo data: org=%s node=%s", self.org_id, self.node_id)

    def publish_forever(self) -> None:
        auth = None
        if self.settings.mqtt_username:
            auth = {"username": self.settings.mqtt_username, "password": self.settings.mqtt_password or ""}

        battery = 95.0
        while True:
            moisture = max(0.05, min(0.9, random.gauss(0.35, 0.08)))
            temperature = random.gauss(21.0, 1.5)
            battery = max(5.0, battery - random.random() * 0.05)
            payload = {
                "org_id": str(self.org_id),
                "node_id": str(self.node_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "battery_level": round(battery, 2),
                "temperature": round(temperature, 2),
                "moisture": round(moisture, 3),
            }
            topic = f"org/{self.org_id}/nodes/{self.node_id}/telemetry"
            publish.single(
                topic,
                payload=json.dumps(payload),
                hostname=self.settings.mqtt_host,
                port=self.settings.mqtt_port,
                auth=auth,
            )
            logger.info("Published telemetry %s", payload)
            time.sleep(5)


def main() -> None:
    settings = Settings()
    ctx = SeedContext(settings)
    ctx.seed()
    ctx.publish_forever()


if __name__ == "__main__":
    main()
