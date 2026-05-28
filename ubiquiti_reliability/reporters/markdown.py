from __future__ import annotations

from pathlib import Path

from ubiquiti_reliability.models import ReliabilityReport


def write_markdown_report(report: ReliabilityReport, path: str | Path) -> Path:
    output = Path(path)
    lines = [
        f"# Ubiquiti Reliability Report - {report.month}",
        "",
        "Operational estimate from normalized telemetry. Not a customer-facing SLA statement.",
        "",
        "## Summary",
        "",
        f"- Incidents: {report.summary.incident_count}",
        f"- Total impact: {report.summary.total_impact_value:.3f} {report.summary.impact_units.replace('_', ' ')}",
        f"- Device snapshots: {report.summary.source_coverage.get('device_snapshots', 0)}",
        f"- Client snapshots: {report.summary.source_coverage.get('client_snapshots', 0)}",
        f"- Events: {report.summary.source_coverage.get('events', 0)}",
        "",
        "## Cause Buckets",
        "",
    ]
    if report.summary.cause_bucket_totals:
        lines.extend(["| Cause | Impact |", "|---|---:|"])
        for cause, value in report.summary.cause_bucket_totals.items():
            lines.append(f"| {cause} | {value:.3f} |")
    else:
        lines.append("No incident causes detected.")
    lines.extend(["", "## Incidents", ""])
    if report.incidents:
        lines.extend([
            "| ID | Window | Scope | Cause | Confidence | Impact |",
            "|---|---|---|---|---|---:|",
        ])
        for incident in report.incidents:
            lines.append(
                "| {id} | {start} to {end} | {scope} | {cause} | {confidence} | {impact:.3f} {units} |".format(
                    id=incident.incident_id,
                    start=incident.start_time.strftime("%Y-%m-%d %H:%MZ"),
                    end=incident.end_time.strftime("%Y-%m-%d %H:%MZ"),
                    scope=incident.scope_name,
                    cause=incident.cause_bucket,
                    confidence=incident.confidence,
                    impact=incident.impact_value,
                    units=incident.impact_units.replace("_", " "),
                )
            )
    else:
        lines.append("No outage-like incident windows detected for this month.")
    lines.extend(["", "## Limitations", ""])
    for limitation in report.limitations or report.summary.limitations:
        lines.append(f"- {limitation}")
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output

