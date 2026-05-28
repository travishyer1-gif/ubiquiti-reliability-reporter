from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ubiquiti_reliability.api_probe import probe_provider
from ubiquiti_reliability.audit import audit_public_repo, write_audit_json
from ubiquiti_reliability.collectors.fixtures import FixtureCollector
from ubiquiti_reliability.incident import build_report
from ubiquiti_reliability.reporters.excel import write_excel_report
from ubiquiti_reliability.reporters.json_report import write_json_report
from ubiquiti_reliability.reporters.markdown import write_markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate-fixtures":
        return cmd_validate_fixtures(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "probe":
        return cmd_probe(args)
    if args.command == "audit-public":
        return cmd_audit_public(args)
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ubiquiti-reliability", description="Ubiquiti-style reliability report generator")
    sub = parser.add_subparsers(dest="command")

    validate = sub.add_parser("validate-fixtures", help="Validate sanitized public fixture data")
    validate.add_argument("path")

    report = sub.add_parser("report", help="Generate monthly report outputs")
    report.add_argument("--source", choices=["fixtures"], required=True)
    report.add_argument("--input", required=True)
    report.add_argument("--month", required=True)
    report.add_argument("--output-dir", required=True)

    probe = sub.add_parser("probe", help="Write read-only API feasibility artifact")
    probe.add_argument("--provider", choices=["unifi", "uisp"], required=True)
    probe.add_argument("--config")
    probe.add_argument("--base-url-file")
    probe.add_argument("--token-file")
    probe.add_argument("--redacted-output", required=True)
    probe.add_argument("--timeout-seconds", type=float, default=10.0)

    audit = sub.add_parser("audit-public", help="Audit repo contents for public/private boundary issues")
    audit.add_argument("path")
    audit.add_argument("--json-output")
    return parser


def cmd_validate_fixtures(args) -> int:
    collector = FixtureCollector(args.path)
    errors = collector.validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"fixtures valid: {args.path}")
    return 0


def cmd_report(args) -> int:
    collector = FixtureCollector(args.input)
    errors = collector.validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    bundle = collector.collect()
    reliability_report = build_report(bundle, args.month)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = write_markdown_report(reliability_report, output_dir / f"reliability-{args.month}.md")
    json_path = write_json_report(reliability_report, output_dir / f"reliability-{args.month}.json")
    xlsx_path = write_excel_report(reliability_report, output_dir / f"reliability-{args.month}.xlsx")
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    print(f"wrote {xlsx_path}")
    return 0


def cmd_probe(args) -> int:
    output = probe_provider(
        args.provider,
        output_path=args.redacted_output,
        config_path=args.config,
        base_url_file=args.base_url_file,
        token_file=args.token_file,
        timeout_seconds=args.timeout_seconds,
    )
    print(f"wrote {output}")
    return 0


def cmd_audit_public(args) -> int:
    result = audit_public_repo(args.path)
    if args.json_output:
        output = write_audit_json(result, args.json_output)
        print(f"wrote {output}")
    else:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if result.ok:
        print("public audit passed")
        return 0
    for failure in result.failures:
        print(failure, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
