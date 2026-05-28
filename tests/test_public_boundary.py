from pathlib import Path


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

