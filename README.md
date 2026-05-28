# Ubiquiti Reliability Reporter

Fixture-first Python tooling for turning Ubiquiti-style telemetry into monthly reliability reports.

The project is designed for public use: it ships with sanitized examples, no live credentials, and read-only collector contracts. It demonstrates:

- normalized device, client, event, evidence, incident, and report models
- sanitized fixture collection and validation
- incident grouping from offline, restore, WAN, power, RF, congestion, and maintenance events
- first-pass cause classification with confidence labels
- impact estimates in device-hours or client-hours
- Markdown, JSON, and Excel workbook outputs
- privacy checks that reject obvious public fixture leaks
- documented boundary for private operator-specific adapters

## Install

```bash
python -m pip install -e .
```

This exposes the `ubiquiti-reliability` CLI.

## Local Usage

From the repository root after installation:

```bash
ubiquiti-reliability validate-fixtures examples/sanitized

ubiquiti-reliability report \
  --source fixtures \
  --input examples/sanitized \
  --month 2026-05 \
  --output-dir reports/sample-2026-05
```

Without installing, run with `PYTHONPATH`:

```bash
PYTHONPATH=. python -m ubiquiti_reliability.cli report \
  --source fixtures \
  --input examples/sanitized \
  --month 2026-05 \
  --output-dir reports/sample-2026-05
```

Generated outputs include:

- `reliability-YYYY-MM.md`
- `reliability-YYYY-MM.json`
- `reliability-YYYY-MM.xlsx`

## Public Audit

Run this before publishing or cutting a release:

```bash
ubiquiti-reliability audit-public .
```

The audit flags cache/build artifacts and fails on secret-like assignments, private adapter imports, and non-sanitized public fixtures.

## Tests

```bash
python -m pip install -e . pytest
pytest -q
```

## Public Boundary

The public core does not import billing systems, mailbox systems, internal topology databases, customer databases, or private network scripts. Public fixtures use generic documentation-range IP addresses and synthetic identifiers only.

Private adapters may be added later outside this package to enrich reports with customer-hours, billing state, email-inferred incidents, QoE telemetry, or internal topology. Those adapters must hand sanitized normalized records to the public core and must not ship public fixtures containing customer data.

## No SLA Claims

Reports produced by this proof-of-work are operational estimates, not customer-facing SLA statements. They include source coverage and limitations so operators can see whether a number came from strong telemetry, fixture data, or partial evidence.

## License

MIT. See `LICENSE`.
