# Read-Only API Feasibility Notes

Current public documentation supports a read-only feasibility path:

- UniFi Site Manager API exposes high-level Internet health, device status, and network performance across sites.
- Local UniFi Network APIs expose UniFi devices, client activity, traffic insights, and similar controller-local data.
- UniFi system logs can be exported to SIEM/syslog in Common Event Format and include useful event categories such as Monitoring, Internet, Power, Security, and System.

Phase 1 collector stance:

- Fixture collector is the deterministic public core.
- Live UniFi and UISP collectors should begin as read-only probes that summarize endpoint shape, field availability, source retention, and limitations.
- Real incident reconstruction should combine snapshots with exported logs/syslog where API history is shallow.

The CLI `probe` command writes a redacted artifact. It records endpoint names, method `GET`, HTTP status, response shape, and unlocks needed. It never stores token values or raw controller payloads.

