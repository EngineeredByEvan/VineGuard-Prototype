from __future__ import annotations

"""Telemetry validation helpers."""

from datetime import datetime
from typing import Any, Dict


class TelemetryValidationError(ValueError):
    """Raised when telemetry payloads do not match the schema."""


class TelemetryValidator:
    """Validates and normalises telemetry payloads."""

    REQUIRED_STRING_FIELDS = ("nodeId", "orgId", "siteId")
    TIMESTAMP_FIELD = "timestamp"
    METRICS_FIELD = "metrics"

    def validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TelemetryValidationError("Telemetry payload must be a JSON object")

        for field in self.REQUIRED_STRING_FIELDS:
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise TelemetryValidationError(f"Field '{field}' must be a non-empty string")

        timestamp = payload.get(self.TIMESTAMP_FIELD)
        if not isinstance(timestamp, str) or not timestamp:
            raise TelemetryValidationError("Telemetry payload must include an ISO8601 'timestamp'")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:  # pragma: no cover - defensive
            raise TelemetryValidationError("Telemetry timestamp is not a valid ISO8601 string") from exc

        metrics = payload.get(self.METRICS_FIELD)
        if not isinstance(metrics, dict) or not metrics:
            raise TelemetryValidationError("Telemetry payload must include a non-empty 'metrics' object")
        for key, value in metrics.items():
            if not isinstance(key, str) or not key:
                raise TelemetryValidationError("Metric keys must be non-empty strings")
            if not isinstance(value, (int, float)):
                raise TelemetryValidationError(f"Metric '{key}' must be numeric")

        return payload


__all__ = ["TelemetryValidator", "TelemetryValidationError"]
