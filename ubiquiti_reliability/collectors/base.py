from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ubiquiti_reliability.models import ClientSnapshot, DeviceSnapshot, ReliabilityEvent


@dataclass(frozen=True)
class TelemetryBundle:
    devices: list[DeviceSnapshot]
    clients: list[ClientSnapshot]
    events: list[ReliabilityEvent]


class Collector(Protocol):
    def collect(self) -> TelemetryBundle:
        """Return normalized telemetry without mutating source systems."""

