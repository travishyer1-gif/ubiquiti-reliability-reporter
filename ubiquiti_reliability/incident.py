from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha1

from ubiquiti_reliability.collectors.base import TelemetryBundle
from ubiquiti_reliability.models import EvidenceRef, Incident, ReliabilityReport, ReportSummary


START_EVENT_TYPES = {
    "device_offline",
    "ap_offline",
    "site_down",
    "wan_down",
    "power_loss",
    "rf_interference",
    "congestion",
    "client_degraded",
    "maintenance_started",
    "config_change",
}
END_EVENT_TYPES = {
    "device_online",
    "ap_online",
    "site_online",
    "wan_restored",
    "power_restored",
    "maintenance_ended",
    "congestion_cleared",
    "rf_clear",
}
DEFAULT_DURATION = timedelta(minutes=15)
MERGE_GAP = timedelta(minutes=10)


@dataclass
class _Window:
    start_time: datetime
    end_time: datetime
    scope_type: str
    scope_id: str
    site_id: str
    events: list


def build_report(bundle: TelemetryBundle, month: str) -> ReliabilityReport:
    incidents = reconstruct_incidents(bundle, month)
    limitations: list[str] = []
    if not bundle.devices and not bundle.clients and not bundle.events:
        limitations.append("No fixture telemetry was supplied; report contains no incidents.")
    if not incidents and bundle.events:
        limitations.append("Telemetry was present, but no outage-like incident windows were detected.")
    if incidents:
        limitations.append("Impact is estimated from fixture device/client snapshots and is not a customer-facing SLA.")
    summary = summarize_incidents(incidents, bundle, month, limitations)
    return ReliabilityReport(
        month=month,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        incidents=incidents,
        limitations=limitations,
    )


def reconstruct_incidents(bundle: TelemetryBundle, month: str) -> list[Incident]:
    events = [event for event in sorted(bundle.events, key=lambda item: item.timestamp) if event.timestamp.strftime("%Y-%m") == month]
    windows = _events_to_windows(events)
    merged = _merge_windows(windows)
    return [_window_to_incident(window, bundle, index + 1) for index, window in enumerate(merged)]


def summarize_incidents(
    incidents: list[Incident],
    bundle: TelemetryBundle,
    month: str,
    limitations: list[str],
) -> ReportSummary:
    cause_totals: dict[str, float] = defaultdict(float)
    confidence_totals: Counter[str] = Counter()
    for incident in incidents:
        cause_totals[incident.cause_bucket] += incident.impact_value
        confidence_totals[incident.confidence] += 1
    primary_units = "client_hours" if any(item.impact_units == "client_hours" for item in incidents) else "device_hours"
    total = sum(item.impact_value for item in incidents if item.impact_units == primary_units)
    worst = sorted(incidents, key=lambda item: item.impact_value, reverse=True)[:5]
    sources = Counter([item.source for item in bundle.events])
    return ReportSummary(
        month=month,
        incident_count=len(incidents),
        total_impact_value=round(total, 3),
        impact_units=primary_units,
        worst_incidents=[
            {
                "incident_id": item.incident_id,
                "scope_name": item.scope_name,
                "impact_units": item.impact_units,
                "impact_value": item.impact_value,
                "cause_bucket": item.cause_bucket,
                "confidence": item.confidence,
            }
            for item in worst
        ],
        cause_bucket_totals={key: round(value, 3) for key, value in sorted(cause_totals.items())},
        confidence_totals=dict(confidence_totals),
        source_coverage={
            "device_snapshots": len(bundle.devices),
            "client_snapshots": len(bundle.clients),
            "events": len(bundle.events),
            "event_sources": dict(sources),
        },
        limitations=list(limitations),
    )


def classify_cause(messages: list[str], event_types: list[str]) -> str:
    text = " ".join(messages + event_types).lower()
    if any(token in text for token in ("power", "poe", "underpowered", "battery", "ups")):
        return "power"
    if any(token in text for token in ("wan", "carrier", "failover", "internet outage", "packet loss")):
        return "WAN_carrier"
    if any(token in text for token in ("gateway", "udm", "router")):
        return "gateway"
    if "switch" in text:
        return "switch"
    if any(token in text for token in ("rf", "interference", "rssi", "noise")):
        return "RF_interference"
    if any(token in text for token in ("ap", "radio", "access point")):
        return "AP_radio"
    if any(token in text for token in ("client", "cpe", "station")):
        return "CPE_client"
    if any(token in text for token in ("congestion", "capacity", "airtime", "utilization")):
        return "congestion"
    if any(token in text for token in ("config", "changed", "firmware")):
        return "config_change"
    if "maintenance" in text:
        return "maintenance"
    return "unknown"


def confidence_for(events: list, cause_bucket: str) -> str:
    sources = {event.source for event in events}
    event_types = {event.event_type for event in events}
    if len(sources) >= 2 or (len(events) >= 2 and any(kind in event_types for kind in END_EVENT_TYPES)):
        return "high"
    if cause_bucket != "unknown" and len(events) >= 1:
        return "medium"
    return "low"


def _events_to_windows(events: list) -> list[_Window]:
    windows: list[_Window] = []
    open_by_key: dict[tuple[str, str], object] = {}
    for event in events:
        key = _event_key(event)
        if event.event_type in START_EVENT_TYPES:
            if key in open_by_key:
                prior = open_by_key.pop(key)
                windows.append(_Window(prior.timestamp, event.timestamp, prior.scope_type, prior.scope_id, prior.site_id, [prior]))
            open_by_key[key] = event
        elif event.event_type in END_EVENT_TYPES:
            start = open_by_key.pop(key, None)
            if start:
                windows.append(_Window(start.timestamp, event.timestamp, start.scope_type, start.scope_id, start.site_id, [start, event]))
        elif _looks_outage_like(event):
            windows.append(_Window(event.timestamp, event.timestamp + DEFAULT_DURATION, event.scope_type, event.scope_id, event.site_id, [event]))
    for event in open_by_key.values():
        windows.append(_Window(event.timestamp, event.timestamp + DEFAULT_DURATION, event.scope_type, event.scope_id, event.site_id, [event]))
    return sorted(windows, key=lambda item: (item.site_id, item.scope_type, item.scope_id, item.start_time))


def _merge_windows(windows: list[_Window]) -> list[_Window]:
    merged: list[_Window] = []
    for window in windows:
        if merged and _merge_key(merged[-1]) == _merge_key(window) and window.start_time <= merged[-1].end_time + MERGE_GAP:
            merged[-1].end_time = max(merged[-1].end_time, window.end_time)
            merged[-1].events.extend(window.events)
        else:
            merged.append(window)
    return sorted(merged, key=lambda item: item.start_time)


def _window_to_incident(window: _Window, bundle: TelemetryBundle, ordinal: int) -> Incident:
    duration_seconds = max(0, int((window.end_time - window.start_time).total_seconds()))
    devices = _affected_devices(window, bundle)
    client_count = _affected_client_count(window, bundle, devices)
    impact_units = "client_hours" if client_count else "device_hours"
    multiplier = client_count if client_count else max(len(devices), 1)
    impact_value = round((duration_seconds / 3600.0) * multiplier, 3)
    messages = [event.message for event in window.events]
    event_types = [event.event_type for event in window.events]
    cause = classify_cause(messages, event_types)
    confidence = confidence_for(window.events, cause)
    digest = sha1(f"{window.site_id}:{window.scope_type}:{window.scope_id}:{window.start_time.isoformat()}".encode()).hexdigest()[:8]
    scope_name = _scope_name(window, bundle)
    evidence = [
        EvidenceRef(
            source=event.source,
            source_record_id=event.event_id,
            timestamp=event.timestamp,
            summary=event.message,
            confidence_weight=0.8 if event.event_type in START_EVENT_TYPES | END_EVENT_TYPES else 0.4,
            private=False,
        )
        for event in window.events
    ]
    return Incident(
        incident_id=f"inc-{ordinal:03d}-{digest}",
        start_time=window.start_time,
        end_time=window.end_time,
        duration_seconds=duration_seconds,
        scope_type=window.scope_type,
        scope_id=window.scope_id,
        scope_name=scope_name,
        affected_device_ids=sorted(devices),
        affected_client_count=client_count,
        impact_units=impact_units,
        impact_value=impact_value,
        cause_bucket=cause,
        confidence=confidence,
        evidence=evidence,
    )


def _event_key(event) -> tuple[str, str]:
    return (_normalized_scope_type(event.scope_type), event.scope_id or event.site_id)


def _merge_key(window: _Window) -> tuple[str, str]:
    return (_normalized_scope_type(window.scope_type), window.scope_id or window.site_id)


def _normalized_scope_type(scope_type: str) -> str:
    return {"access_point": "ap", "radio": "ap", "site": "site"}.get(scope_type, scope_type)


def _looks_outage_like(event) -> bool:
    text = f"{event.event_type} {event.message}".lower()
    return any(token in text for token in ("offline", "outage", "down", "failover", "underpowered", "interference", "congestion"))


def _affected_devices(window: _Window, bundle: TelemetryBundle) -> set[str]:
    if window.scope_type == "site":
        return {device.device_id for device in bundle.devices if device.site_id == window.site_id}
    device_ids = {window.scope_id} if window.scope_id else set()
    children = {device.device_id for device in bundle.devices if device.parent_device_id == window.scope_id}
    return device_ids | children


def _affected_client_count(window: _Window, bundle: TelemetryBundle, devices: set[str]) -> int:
    explicit = [event.metadata.get("affected_client_count") for event in window.events if isinstance(event.metadata.get("affected_client_count"), int)]
    if explicit:
        return max(explicit)
    if window.scope_type == "site":
        return len({client.client_id for client in bundle.clients if client.site_id == window.site_id})
    return len({client.client_id for client in bundle.clients if client.connected_to_device_id in devices})


def _scope_name(window: _Window, bundle: TelemetryBundle) -> str:
    for device in bundle.devices:
        if device.device_id == window.scope_id:
            return device.device_name
    for device in bundle.devices:
        if device.site_id == window.site_id:
            return device.site_name
    return window.scope_id or window.site_id or "unknown"
