from __future__ import annotations

import json
from pathlib import Path

from ubiquiti_reliability.collectors.base import TelemetryBundle
from ubiquiti_reliability.models import ClientSnapshot, DeviceSnapshot, ReliabilityEvent
from ubiquiti_reliability.privacy import validate_public_fixture_dir


class FixtureCollector:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def validate(self) -> list[str]:
        errors = validate_public_fixture_dir(self.root)
        for filename in ("devices.json", "clients.json", "events.json"):
            path = self.root / filename
            if not path.exists():
                errors.append(f"{path}: required fixture file is missing")
        if errors:
            return errors
        try:
            self.collect()
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{self.root}: fixture schema error: {exc}")
        return errors

    def collect(self) -> TelemetryBundle:
        devices_data = _load_json_list(self.root / "devices.json")
        clients_data = _load_json_list(self.root / "clients.json")
        events_data = _load_json_list(self.root / "events.json")
        return TelemetryBundle(
            devices=[DeviceSnapshot.from_dict(item) for item in devices_data],
            clients=[ClientSnapshot.from_dict(item) for item in clients_data],
            events=[ReliabilityEvent.from_dict(item) for item in events_data],
        )


def _load_json_list(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected JSON array")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path}[{index}]: expected object")
    return data

