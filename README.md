# Ubiquiti Reliability Reporter

Turn messy Ubiquiti-style network telemetry into executive-ready monthly reliability reports.

This repo is a public, sanitized proof-of-work for a problem every small ISP and MSP runs into: the network has plenty of device events, client snapshots, and controller data, but leadership needs a clean answer to a simpler question:

> What happened this month, what caused it, how many client-hours did it affect, and how confident are we?

## What It Demonstrates

- A fixture-first Python package that normalizes devices, clients, events, incidents, evidence, and reports.
- Incident grouping from offline, restore, WAN, power, RF, congestion, and maintenance events.
- Cause classification with confidence labels instead of pretending every diagnosis is certain.
- Client-hour and device-hour impact estimates.
- Markdown, JSON, and Excel report output from the same normalized report model.
- A public/private boundary that keeps operator-specific adapters out of the public package.
- A built-in public audit command that catches obvious fixture leaks, private imports, secrets, and cache artifacts before publishing.

## 30-Second Demo

```bash
python -m pip install -e . pytest
ubiquiti-reliability validate-fixtures examples/sanitized
ubiquiti-reliability report \
  --source fixtures \
  --input examples/sanitized \
  --month 2026-05 \
  --output-dir reports/sample-2026-05
```

Example report output:

```text
Incidents: 3
Total impact: 2.417 client hours
Events: 7

Cause buckets:
- power: 1.167 client hours
- WAN_carrier: 0.750 client hours
- RF_interference: 0.500 client hours
```

Generated files:

```text
reports/sample-2026-05/reliability-2026-05.md
reports/sample-2026-05/reliability-2026-05.json
reports/sample-2026-05/reliability-2026-05.xlsx
```

## Why This Exists

Ubiquiti controllers are useful for operations, but the raw event stream is not the same thing as a monthly reliability narrative. A good operator report needs to:

- separate real incidents from noisy controller events
- preserve source coverage and limitations
- estimate customer impact without overclaiming SLA precision
- support private data enrichment without leaking customer data into public code
- produce artifacts that can drop into monthly reporting workflows

This repo focuses on that translation layer.

## Public Safety Boundary

The public core does not import billing systems, mailbox systems, customer databases, internal topology databases, or private network scripts. Public fixtures use synthetic identifiers and documentation-range IP addresses only.

Private operators can build separate adapters that hand sanitized normalized records to this package. Those adapters should stay outside this repo.

Run the audit before publishing changes:

```bash
ubiquiti-reliability audit-public .
```

The audit fails on secret-like assignments, private adapter imports, missing sanitized fixtures, and fixture data that looks like customer information.

## Architecture

```text
fixtures / future read-only adapters
        |
        v
normalized telemetry bundle
        |
        v
incident grouping + cause classification
        |
        v
ReliabilityReport model
        |
        +--> Markdown report
        +--> JSON report
        +--> Excel workbook
```

Core modules:

- `ubiquiti_reliability.models` - typed telemetry and report records
- `ubiquiti_reliability.collectors.fixtures` - sanitized fixture loader and validator
- `ubiquiti_reliability.incident` - incident grouping, classification, impact calculation
- `ubiquiti_reliability.reporters` - Markdown, JSON, and XLSX writers
- `ubiquiti_reliability.audit` - public repo boundary audit
- `ubiquiti_reliability.api_probe` - redacted read-only API feasibility artifact helper

## Commands

Validate public fixtures:

```bash
ubiquiti-reliability validate-fixtures examples/sanitized
```

Generate reports:

```bash
ubiquiti-reliability report \
  --source fixtures \
  --input examples/sanitized \
  --month 2026-05 \
  --output-dir reports/sample-2026-05
```

Audit public safety:

```bash
ubiquiti-reliability audit-public .
```

Write a redacted read-only API feasibility artifact:

```bash
ubiquiti-reliability probe \
  --provider uisp \
  --base-url-file /path/to/base-url \
  --token-file /path/to/token \
  --redacted-output reports/uisp-feasibility.json
```

## Tests

```bash
python -m pip install -e . pytest
pytest -q
```

Current local verification:

```text
15 passed
fixtures valid: examples/sanitized
public audit passed with failures: [] and warnings: []
```

## What This Is Not

This is not a customer-facing SLA engine. It is an operational reporting layer that preserves limitations and confidence so the output can be used responsibly.

It is also not a live controller exporter. The public package includes read-only probe scaffolding and sanitized fixtures; production adapters belong in private repos or private deployment code.

## License

MIT. See `LICENSE`.
