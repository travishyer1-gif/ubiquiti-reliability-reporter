from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ubiquiti_reliability.privacy import redact_value


READ_ONLY_ENDPOINTS = {
    "uisp": ["devices", "sites"],
    "unifi": ["v1/info", "v1/sites"],
}


def probe_provider(
    provider: str,
    *,
    output_path: str | Path,
    config_path: str | Path | None = None,
    base_url_file: str | Path | None = None,
    token_file: str | Path | None = None,
    timeout_seconds: float = 10.0,
) -> Path:
    provider = provider.lower()
    if provider not in READ_ONLY_ENDPOINTS:
        raise ValueError(f"unsupported provider: {provider}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    config = _load_probe_config(config_path, base_url_file, token_file)
    artifact: dict[str, Any] = {
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "read_only",
        "mutating_methods_used": [],
        "endpoints_requested": READ_ONLY_ENDPOINTS[provider],
        "status": "blocked",
        "findings": [],
        "unlocks_needed": [],
    }
    if not config.get("base_url"):
        artifact["unlocks_needed"].append("Provide provider base_url through a private config or --base-url-file.")
    if not config.get("token"):
        artifact["unlocks_needed"].append("Provide read-only API token through a private config or --token-file.")
    if artifact["unlocks_needed"]:
        output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return output
    artifact["status"] = "attempted"
    base_url = _normalized_base_url(provider, config["base_url"])
    for endpoint in READ_ONLY_ENDPOINTS[provider]:
        artifact["findings"].append(_read_endpoint(base_url, endpoint, config["token"], timeout_seconds))
    if any(item.get("ok") and item.get("json") for item in artifact["findings"]):
        artifact["status"] = "success"
    else:
        artifact["status"] = "attempted_no_successful_reads"
        artifact["unlocks_needed"].append("Verify API base URL, token permissions, network reachability, certificate trust, and JSON API path.")
    output.write_text(json.dumps(redact_value(artifact), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _load_probe_config(config_path, base_url_file, token_file) -> dict[str, str | None]:
    config: dict[str, str | None] = {"base_url": None, "token": None}
    if config_path:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        config["base_url"] = data.get("base_url")
        config["token"] = data.get("token")
        if data.get("base_url_file"):
            config["base_url"] = Path(data["base_url_file"]).read_text(encoding="utf-8").strip()
        if data.get("token_file"):
            config["token"] = Path(data["token_file"]).read_text(encoding="utf-8").strip()
    if base_url_file:
        config["base_url"] = Path(base_url_file).read_text(encoding="utf-8").strip()
    if token_file:
        config["token"] = Path(token_file).read_text(encoding="utf-8").strip()
    return config


def _read_endpoint(base_url: str, endpoint: str, token: str, timeout_seconds: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "X-Auth-Token": token,
            "Authorization": f"Bearer {token}",
            "User-Agent": "ubiquiti-reliability-reporter/0.1 read-only-probe",
        },
    )
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            raw = response.read(256_000)
            parsed = _try_json(raw)
            return {
                "endpoint": endpoint,
                "method": "GET",
                "ok": 200 <= response.status < 300,
                "json": not (isinstance(parsed, dict) and parsed.get("json") is False),
                "http_status": response.status,
                "shape": _shape_summary(parsed),
            }
    except urllib.error.HTTPError as exc:
        return {"endpoint": endpoint, "method": "GET", "ok": False, "http_status": exc.code, "error": "http_error"}
    except Exception as exc:
        return {"endpoint": endpoint, "method": "GET", "ok": False, "error": type(exc).__name__}


def _try_json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"json": raw.lstrip()[:1] in (b"{", b"["), "truncated_or_unparsed": True}


def _normalized_base_url(provider: str, base_url: str) -> str:
    if provider != "uisp":
        return base_url
    parsed = urllib.parse.urlparse(base_url)
    if parsed.path and parsed.path != "/":
        return base_url
    return base_url.rstrip("/") + "/nms/api/v2.1"


def _shape_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        first = value[0] if value else {}
        return {
            "top_level_type": "list",
            "items_seen": "nonempty" if value else "empty",
            "sample_keys": sorted(first.keys())[:30] if isinstance(first, dict) else [],
        }
    if isinstance(value, dict):
        data = value.get("data")
        return {
            "top_level_type": "dict",
            "top_level_keys": sorted(value.keys())[:30],
            "data_shape": _shape_summary(data) if isinstance(data, (list, dict)) else None,
        }
    return {"top_level_type": type(value).__name__}
