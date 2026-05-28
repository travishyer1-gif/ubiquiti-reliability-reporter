from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ubiquiti_reliability.privacy import validate_public_fixture_dir


PRIVATE_IMPORT_PATTERNS = (
    re.compile(r"^\s*(?:from|import)\s+scripts(?:\.|\s|$)", re.MULTILINE),
    re.compile(r"^\s*(?:from|import)\s+preseem(?:\.|\s|$)", re.MULTILINE),
    re.compile(r"^\s*(?:from|import)\s+visp(?:\.|\s|$)", re.MULTILINE),
    re.compile(r"^\s*(?:from|import)\s+outlook(?:\.|\s|$)", re.MULTILINE),
    re.compile(r"^\s*(?:from|import)\s+projects\.advantage", re.MULTILINE),
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|authorization|bearer)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)x-auth-token\s*[:=]"),
)
DISALLOWED_DIRS = {".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}
DISALLOWED_SUFFIXES = {".pyc", ".pyo"}
IGNORED_DIRS = {".git", ".hg", ".svn"}


@dataclass
class PublicAuditResult:
    ok: bool
    checked_root: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def audit_public_repo(root: str | Path) -> PublicAuditResult:
    project_root = Path(root).resolve()
    failures: list[str] = []
    warnings: list[str] = []
    if not project_root.exists():
        return PublicAuditResult(False, str(project_root), [f"{project_root}: path does not exist"], [])

    for path in sorted(project_root.rglob("*")):
        rel = path.relative_to(project_root)
        parts = set(rel.parts)
        if parts & IGNORED_DIRS:
            continue
        if path.is_dir() and path.name in DISALLOWED_DIRS:
            warnings.append(f"{rel}: generated cache directory should be removed before publishing")
            continue
        if not path.is_file():
            continue
        if parts & DISALLOWED_DIRS:
            warnings.append(f"{rel}: generated cache artifact should be removed before publishing")
            continue
        if path.suffix in DISALLOWED_SUFFIXES:
            warnings.append(f"{rel}: compiled Python artifact should be removed before publishing")
            continue
        if path.name.lower() in {".env", ".env.local"}:
            failures.append(f"{rel}: environment file must not be published")
            continue
        if _is_text_path(path):
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    failures.append(f"{rel}: secret-like assignment found")
            if path.suffix == ".py":
                for pattern in PRIVATE_IMPORT_PATTERNS:
                    if pattern.search(text):
                        failures.append(f"{rel}: private/internal import boundary violation")
        elif path.suffix.lower() not in {".xlsx", ".png", ".jpg", ".jpeg", ".gif"}:
            warnings.append(f"{rel}: binary or unknown file type included; review before publishing")

    fixtures = project_root / "examples" / "sanitized"
    if fixtures.exists():
        failures.extend(validate_public_fixture_dir(fixtures))
    else:
        failures.append("examples/sanitized: sanitized fixture directory is missing")

    return PublicAuditResult(not failures, str(project_root), failures, warnings)


def write_audit_json(result: PublicAuditResult, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _is_text_path(path: Path) -> bool:
    return path.suffix.lower() in {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".txt", ".gitignore", ""}
