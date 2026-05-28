# Private Adapter Boundary

The public package stops at normalized telemetry, incident reconstruction, and report outputs. It must remain importable without operator-specific private systems.

Allowed private adapters later:

- customer-hours enrichment from a private subscriber system
- QoE/context enrichment from private performance telemetry
- email-inferred outage evidence from private mailbox workflows
- private topology joins from an internal network twin
- carrier notice joins from internal operations records

Private adapters should return public-core records:

- `DeviceSnapshot`
- `ClientSnapshot`
- `ReliabilityEvent`
- `EvidenceRef`

Rules:

- No private adapter imports inside `ubiquiti_reliability`.
- No customer names, account IDs, billing fields, addresses, phone numbers, emails, private notes, credentials, or real topology identifiers in public fixtures.
- Public reports default to device-hours or client-hours. Customer-hours require a private adapter and must stay out of public fixtures.
- Live collectors must be read-only and must never issue POST, PUT, PATCH, or DELETE against controllers.
