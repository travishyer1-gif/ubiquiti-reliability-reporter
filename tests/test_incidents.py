from pathlib import Path

from ubiquiti_reliability.collectors.fixtures import FixtureCollector
from ubiquiti_reliability.incident import build_report, classify_cause, reconstruct_incidents


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "sanitized"


def test_adjacent_ap_events_merge_into_one_incident():
    bundle = FixtureCollector(FIXTURES).collect()
    incidents = reconstruct_incidents(bundle, "2026-05")
    ap_incidents = [item for item in incidents if item.scope_id == "ap-north-1" and item.cause_bucket == "power"]
    assert len(ap_incidents) == 1
    assert ap_incidents[0].duration_seconds == 35 * 60
    assert ap_incidents[0].affected_client_count == 2
    assert ap_incidents[0].impact_units == "client_hours"
    assert ap_incidents[0].impact_value == 1.167
    assert ap_incidents[0].confidence == "high"


def test_cause_classifier_covers_core_buckets():
    assert classify_cause(["WAN carrier failover"], ["wan_down"]) == "WAN_carrier"
    assert classify_cause(["High airtime and congestion"], ["congestion"]) == "congestion"
    assert classify_cause(["RF interference detected"], ["rf_interference"]) == "RF_interference"
    assert classify_cause(["Firmware config changed"], ["config_change"]) == "config_change"


def test_report_summary_includes_limitations_and_buckets():
    report = build_report(FixtureCollector(FIXTURES).collect(), "2026-05")
    assert report.summary.incident_count == 3
    assert report.summary.cause_bucket_totals["power"] == 1.167
    assert report.summary.cause_bucket_totals["WAN_carrier"] == 0.75
    assert report.summary.cause_bucket_totals["RF_interference"] == 0.5
    assert report.limitations

