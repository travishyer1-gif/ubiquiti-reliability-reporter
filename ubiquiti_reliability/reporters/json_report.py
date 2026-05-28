from __future__ import annotations

import json
from pathlib import Path

from ubiquiti_reliability.models import ReliabilityReport


def write_json_report(report: ReliabilityReport, path: str | Path) -> Path:
    output = Path(path)
    output.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output

