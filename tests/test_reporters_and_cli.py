import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "examples" / "sanitized"


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "ubiquiti_reliability.cli", *args],
        cwd=cwd or PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_validate_fixtures_passes():
    result = run_cli("validate-fixtures", str(FIXTURES))
    assert result.returncode == 0, result.stderr
    assert "fixtures valid" in result.stdout


def test_cli_report_writes_markdown_json_and_excel(tmp_path):
    result = run_cli(
        "report",
        "--source",
        "fixtures",
        "--input",
        str(FIXTURES),
        "--month",
        "2026-05",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    md = tmp_path / "reliability-2026-05.md"
    js = tmp_path / "reliability-2026-05.json"
    xlsx = tmp_path / "reliability-2026-05.xlsx"
    assert md.exists()
    assert js.exists()
    assert xlsx.exists()
    payload = json.loads(js.read_text())
    assert payload["summary"]["incident_count"] == 3
    assert "not a customer-facing SLA" in md.read_text()
    with ZipFile(xlsx) as archive:
        assert "xl/workbook.xml" in archive.namelist()


def test_probe_without_config_writes_unlock_artifact(tmp_path):
    output = tmp_path / "probe.json"
    result = run_cli("probe", "--provider", "unifi", "--redacted-output", str(output))
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text())
    assert payload["status"] == "blocked"
    assert payload["mutating_methods_used"] == []
    assert payload["unlocks_needed"]


def test_cli_public_audit_passes_for_repo_candidate(tmp_path):
    output = tmp_path / "audit.json"
    result = run_cli("audit-public", str(PROJECT_ROOT), "--json-output", str(output))
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text())
    assert payload["ok"] is True
    assert payload["failures"] == []
