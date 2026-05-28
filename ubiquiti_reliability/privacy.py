from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
PRIVATE_MARKERS = (
    "advantage",
    "advantagewisp",
    "froberto",
    "travis",
    "maya",
    "peter barry",
    "visp",
    "preseem",
    "outlook",
    "customer_id",
    "billing",
)
ADDRESS_HINT_RE = re.compile(r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|blvd|way)\b", re.IGNORECASE)
DOCUMENTATION_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")
)


def validate_public_fixture_dir(path: str | Path) -> list[str]:
    root = Path(path)
    errors: list[str] = []
    if not root.exists():
        return [f"{root}: fixture path does not exist"]
    for file_path in sorted(root.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in {".json", ".jsonl", ".csv", ".md", ".txt"}:
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"{file_path}: fixture is not valid UTF-8 text")
                continue
            errors.extend(validate_public_text(text, label=str(file_path)))
            if file_path.suffix.lower() == ".json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    errors.append(f"{file_path}: invalid JSON at line {exc.lineno}: {exc.msg}")
                    continue
                errors.extend(validate_public_values(data, label=str(file_path)))
    return errors


def validate_public_text(text: str, *, label: str) -> list[str]:
    errors: list[str] = []
    if EMAIL_RE.search(text):
        errors.append(f"{label}: contains email-like text")
    if PHONE_RE.search(text):
        errors.append(f"{label}: contains phone-like text")
    if ADDRESS_HINT_RE.search(text):
        errors.append(f"{label}: contains address-like text")
    lowered = text.lower()
    for marker in PRIVATE_MARKERS:
        if marker in lowered:
            errors.append(f"{label}: contains private marker '{marker}'")
    return errors


def validate_public_values(value: Any, *, label: str, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in {"customer_id", "subscriber_id", "account_number", "invoice_id"}:
                errors.append(f"{label}:{path}.{key}: customer/account field is not public-safe")
            errors.extend(validate_public_values(child, label=label, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(validate_public_values(child, label=label, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            return errors
        if ip.is_private and not any(ip in network for network in DOCUMENTATION_NETWORKS):
            errors.append(f"{label}:{path}: private IP address is not allowed in public fixtures")
    return errors


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            lowered = str(key).lower()
            if (
                lowered in {"token", "api_key", "apikey", "secret", "password", "authorization"}
                or lowered.endswith("_token")
                or lowered.endswith("_secret")
                or lowered.endswith("_password")
                or lowered.endswith("_api_key")
            ):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_value(child)
        return redacted
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        text = EMAIL_RE.sub("<email>", value)
        text = PHONE_RE.sub("<phone>", text)
        return text
    return value
