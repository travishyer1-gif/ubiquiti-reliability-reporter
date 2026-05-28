from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Confidence = Literal["high", "medium", "low"]
PrivacyClass = Literal["public_safe_fixture", "private_internal", "customer_pii"]


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty ISO-8601 string")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DeviceSnapshot:
    source: str
    observed_at: datetime
    site_id: str
    site_name: str
    device_id: str
    device_name: str
    device_type: str
    mac: str
    ip: str
    parent_device_id: str | None
    status: str
    uptime_seconds: int | None = None
    firmware: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceSnapshot":
        return cls(
            source=str(data.get("source", "")),
            observed_at=parse_timestamp(data["observed_at"]),
            site_id=str(data.get("site_id", "")),
            site_name=str(data.get("site_name", "")),
            device_id=str(data.get("device_id", "")),
            device_name=str(data.get("device_name", "")),
            device_type=str(data.get("device_type", "")),
            mac=str(data.get("mac", "")),
            ip=str(data.get("ip", "")),
            parent_device_id=data.get("parent_device_id"),
            status=str(data.get("status", "")),
            uptime_seconds=data.get("uptime_seconds"),
            firmware=data.get("firmware"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["observed_at"] = isoformat(self.observed_at)
        return output


@dataclass(frozen=True)
class ClientSnapshot:
    source: str
    observed_at: datetime
    site_id: str
    client_id: str
    client_name: str
    mac: str
    ip: str
    connected_to_device_id: str
    rssi: int | None
    tx_rate: float | None
    rx_rate: float | None
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientSnapshot":
        return cls(
            source=str(data.get("source", "")),
            observed_at=parse_timestamp(data["observed_at"]),
            site_id=str(data.get("site_id", "")),
            client_id=str(data.get("client_id", "")),
            client_name=str(data.get("client_name", "")),
            mac=str(data.get("mac", "")),
            ip=str(data.get("ip", "")),
            connected_to_device_id=str(data.get("connected_to_device_id", "")),
            rssi=data.get("rssi"),
            tx_rate=data.get("tx_rate"),
            rx_rate=data.get("rx_rate"),
            status=str(data.get("status", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["observed_at"] = isoformat(self.observed_at)
        return output


@dataclass(frozen=True)
class ReliabilityEvent:
    source: str
    event_id: str
    timestamp: datetime
    site_id: str
    scope_type: str
    scope_id: str
    event_type: str
    severity: str
    message: str
    raw_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReliabilityEvent":
        return cls(
            source=str(data.get("source", "")),
            event_id=str(data.get("event_id", "")),
            timestamp=parse_timestamp(data["timestamp"]),
            site_id=str(data.get("site_id", "")),
            scope_type=str(data.get("scope_type", "")),
            scope_id=str(data.get("scope_id", "")),
            event_type=str(data.get("event_type", "")),
            severity=str(data.get("severity", "")),
            message=str(data.get("message", "")),
            raw_ref=data.get("raw_ref"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["timestamp"] = isoformat(self.timestamp)
        return output


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    source_record_id: str
    timestamp: datetime
    summary: str
    confidence_weight: float
    private: bool = False

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["timestamp"] = isoformat(self.timestamp)
        return output


@dataclass
class Incident:
    incident_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    scope_type: str
    scope_id: str
    scope_name: str
    affected_device_ids: list[str]
    affected_client_count: int
    impact_units: str
    impact_value: float
    cause_bucket: str
    confidence: Confidence
    evidence: list[EvidenceRef]
    privacy_class: PrivacyClass = "public_safe_fixture"

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["start_time"] = isoformat(self.start_time)
        output["end_time"] = isoformat(self.end_time)
        output["evidence"] = [item.to_dict() for item in self.evidence]
        return output


@dataclass
class ReportSummary:
    month: str
    incident_count: int
    total_impact_value: float
    impact_units: str
    worst_incidents: list[dict[str, Any]]
    cause_bucket_totals: dict[str, float]
    confidence_totals: dict[str, int]
    source_coverage: dict[str, Any]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReliabilityReport:
    month: str
    generated_at: datetime
    summary: ReportSummary
    incidents: list[Incident]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "generated_at": isoformat(self.generated_at),
            "summary": self.summary.to_dict(),
            "incidents": [incident.to_dict() for incident in self.incidents],
            "limitations": self.limitations,
        }

