from pathlib import Path
import json

from ubiquiti_reliability.collectors.fixtures import FixtureCollector
from ubiquiti_reliability.incident import build_report
from ubiquiti_reliability.privacy import validate_public_text


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "sanitized"


def test_sanitized_fixtures_validate():
    assert FixtureCollector(FIXTURES).validate() == []


def test_fixture_collector_loads_normalized_records():
    bundle = FixtureCollector(FIXTURES).collect()
    assert len(bundle.devices) == 4
    assert len(bundle.clients) == 3
    assert len(bundle.events) == 7
    assert bundle.devices[0].device_id == "gw-north-1"


def test_privacy_guard_rejects_public_fixture_leaks():
    errors = validate_public_text("Contact jane@example.com at 805-555-1212 for customer_id billing", label="bad")
    assert any("email-like" in error for error in errors)
    assert any("phone-like" in error for error in errors)
    assert any("private marker" in error for error in errors)


def test_empty_fixture_data_produces_valid_no_data_report(tmp_path):
    for name in ("devices.json", "clients.json", "events.json"):
        (tmp_path / name).write_text("[]\n", encoding="utf-8")
    collector = FixtureCollector(tmp_path)
    assert collector.validate() == []
    report = build_report(collector.collect(), "2026-05")
    assert report.summary.incident_count == 0
    assert "No fixture telemetry was supplied" in report.limitations[0]


def test_malformed_fixture_validation_reports_schema_error(tmp_path):
    (tmp_path / "devices.json").write_text(json.dumps([{"observed_at": "not-a-date"}]), encoding="utf-8")
    (tmp_path / "clients.json").write_text("[]", encoding="utf-8")
    (tmp_path / "events.json").write_text("[]", encoding="utf-8")
    errors = FixtureCollector(tmp_path).validate()
    assert any("fixture schema error" in error for error in errors)
