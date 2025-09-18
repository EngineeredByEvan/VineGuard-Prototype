from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Deque, Dict, List

from ..models import InsightType
from ..schemas.telemetry import TelemetryPayload


@dataclass(slots=True)
class InsightEvent:
    type: InsightType
    payload: dict


class AnalyticsEngine:
    """Rule-based analytics engine with extension points for ML."""

    def __init__(self, history_size: int = 20) -> None:
        self.history_size = history_size
        self._sensor_history: Dict[str, Dict[str, Deque[float]]] = defaultdict(lambda: defaultdict(deque))
        self._soil_moisture_changes: Dict[str, Deque[float]] = defaultdict(deque)
        self._low_moisture_streak: Dict[str, int] = defaultdict(int)
        self._last_values: Dict[str, Dict[str, float]] = defaultdict(dict)

    def _register_value(self, node_key: str, sensor: str, value: float | None) -> None:
        if value is None:
            return
        history = self._sensor_history[node_key][sensor]
        history.append(value)
        if len(history) > self.history_size:
            history.popleft()

        last_value = self._last_values[node_key].get(sensor)
        if last_value is not None:
            delta = value - last_value
            if sensor == "soil_moisture":
                changes = self._soil_moisture_changes[node_key]
                changes.append(delta)
                if len(changes) > self.history_size:
                    changes.popleft()
        self._last_values[node_key][sensor] = value

    def evaluate(self, telemetry: TelemetryPayload) -> List[InsightEvent]:
        node_key = f"{telemetry.org_id}:{telemetry.site_id}:{telemetry.node_id}"
        events: List[InsightEvent] = []
        sensors = telemetry.sensors

        self._register_value(node_key, "soil_moisture", sensors.soil_moisture)
        self._register_value(node_key, "soil_temp_c", sensors.soil_temp_c)
        self._register_value(node_key, "air_temp_c", sensors.air_temp_c)
        self._register_value(node_key, "humidity", sensors.humidity)
        self._register_value(node_key, "light_lux", sensors.light_lux)
        self._register_value(node_key, "vbat", sensors.vbat)

        # Battery alert
        if sensors.vbat is not None and sensors.vbat < 3.6:
            events.append(
                InsightEvent(
                    type=InsightType.BATTERY,
                    payload={
                        "ts": telemetry.ts.isoformat(),
                        "vbat": sensors.vbat,
                        "message": "Battery voltage below 3.6V",
                    },
                )
            )

        # Sensor range checks
        ranges = {
            "soil_moisture": (0.0, 1.0),
            "soil_temp_c": (-20.0, 60.0),
            "air_temp_c": (-20.0, 60.0),
            "humidity": (0.0, 100.0),
            "light_lux": (0.0, 200000.0),
        }
        for sensor, (lower, upper) in ranges.items():
            value = getattr(sensors, sensor)
            if value is None:
                continue
            if value < lower or value > upper:
                events.append(
                    InsightEvent(
                        type=InsightType.SENSOR_FAULT,
                        payload={
                            "ts": telemetry.ts.isoformat(),
                            "sensor": sensor,
                            "value": value,
                            "message": "Sensor reading out of range",
                        },
                    )
                )

        # Frozen sensor detection (>3 intervals with unchanged value)
        freeze_threshold = 4
        tolerance = 1e-3
        for sensor, history in self._sensor_history[node_key].items():
            if len(history) >= freeze_threshold:
                first = history[-freeze_threshold]
                if all(abs(first - history[-i - 1]) <= tolerance for i in range(freeze_threshold)):
                    events.append(
                        InsightEvent(
                            type=InsightType.SENSOR_FAULT,
                            payload={
                                "ts": telemetry.ts.isoformat(),
                                "sensor": sensor,
                                "message": "Sensor reading unchanged for >3 intervals",
                            },
                        )
                    )

        # Simple anomaly detection: z-score of soil moisture change
        changes = self._soil_moisture_changes[node_key]
        if len(changes) >= 5:
            avg = mean(changes)
            std_dev = pstdev(changes) or 0.0
            if std_dev > 0 and sensors.soil_moisture is not None:
                last_change = changes[-1]
                z_score = abs((last_change - avg) / std_dev)
                if z_score > 3:
                    events.append(
                        InsightEvent(
                            type=InsightType.ANOMALY,
                            payload={
                                "ts": telemetry.ts.isoformat(),
                                "soilMoisture": sensors.soil_moisture,
                                "zScore": z_score,
                                "message": "Soil moisture change deviates >3σ",
                                "TODO": "Replace with ML model once available",
                            },
                        )
                    )

        # Irrigation advice rule
        streak = self._low_moisture_streak[node_key]
        if sensors.soil_moisture is not None and sensors.soil_moisture < 0.25:
            streak += 1
        else:
            streak = 0
        self._low_moisture_streak[node_key] = streak

        if streak >= 3 and sensors.air_temp_c and sensors.humidity is not None:
            vpd = _calculate_vpd(sensors.air_temp_c, sensors.humidity)
            if sensors.air_temp_c > 25 and vpd >= 1.2:
                events.append(
                    InsightEvent(
                        type=InsightType.IRRIGATION,
                        payload={
                            "ts": telemetry.ts.isoformat(),
                            "soilMoisture": sensors.soil_moisture,
                            "airTempC": sensors.air_temp_c,
                            "humidity": sensors.humidity,
                            "vpd": vpd,
                            "message": "Sustained dryness with high VPD",
                        },
                    )
                )

        return events


def _calculate_vpd(air_temp_c: float, humidity: float) -> float:
    # Tetens equation approximation
    es = 0.6108 * 2.718281828 ** ((17.27 * air_temp_c) / (air_temp_c + 237.3))
    ea = es * (humidity / 100.0)
    return max(es - ea, 0.0)
