from pathlib import Path

from ubiquiti_reliability.audit import audit_public_repo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "ubiquiti_reliability"


def test_public_package_does_not_import_private_advantage_modules():
    private_import_terms = (
        "scripts.",
        "projects.advantage",
        "preseem",
        "visp",
        "outlook",
        "advantage_",
    )
    offenders = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in private_import_terms:
            if f"import {term}" in text or f"from {term}" in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {term}")
    assert offenders == []


def test_public_package_mentions_no_customer_facing_sla_claims():
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in PACKAGE_ROOT.rglob("*.py"))
    assert "guaranteed uptime" not in text
    assert "sla credit" not in text


def test_public_audit_ignores_vcs_metadata(tmp_path):
    fixtures = tmp_path / "examples" / "sanitized"
    fixtures.mkdir(parents=True)
    for name in ("devices.json", "clients.json", "events.json"):
        (fixtures / name).write_text("[]\n", encoding="utf-8")
    hook_dir = tmp_path / ".git" / "hooks"
    hook_dir.mkdir(parents=True)
    (hook_dir / "pre-commit.sample").write_bytes(b"\x00\x01")

    result = audit_public_repo(tmp_path)

    assert result.ok
    assert result.failures == []
    assert result.warnings == []
