#!/usr/bin/env python3
"""Shared helpers for Huawei Cloud MaaS API scripts."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import credential_aliases
import hcloud_common

DEFAULT_MAAS_BASE_URL = "https://api.modelarts-maas.com"
MAAS_API_KEY_ENV_NAMES = credential_aliases.MAAS_API_KEY_ENV_NAMES
MAX_SEED = 2_147_483_648
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


class MaasAPIError(RuntimeError):
    """Raised when a MaaS API helper cannot complete safely."""


def endpoint_url(path: str, base_url: str = DEFAULT_MAAS_BASE_URL) -> str:
    """Return a normalized MaaS endpoint URL."""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def api_key_presence() -> dict[str, dict[str, bool]]:
    """Return redacted MaaS API key environment presence."""
    return credential_aliases.credential_environment_presence(MAAS_API_KEY_ENV_NAMES)


def get_api_key() -> str:
    """Read a Huawei Cloud MaaS API key from the environment without logging it."""
    value, _ = credential_aliases.resolve_maas_api_key()
    if value:
        return value
    raise MaasAPIError(
        "缺少华为云 MaaS API Key。请设置 MAAS_API_KEY 或 MODELARTS_MAAS_API_KEY；不要把 API Key 写进代码、命令日志、manifest 或对话。"
    )


def redact_maas_text(text: str | bytes | None, api_key: str | None = None) -> str:
    """Redact MaaS API key material from output text."""
    secrets = set()
    if api_key:
        secrets.add(api_key)
    for name in MAAS_API_KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            secrets.add(value)
    return hcloud_common.redact_text(text, secrets)


def load_json_file(path: Path) -> Any:
    """Load a UTF-8 JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaasAPIError(f"Cannot read JSON file {path}: {exc}") from exc


def load_json_text(value: str) -> Any:
    """Load JSON text with a MaaS-oriented error."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise MaasAPIError(f"Invalid JSON text: {exc}") from exc


def require_json_object(value: Any, source: str) -> dict[str, Any]:
    """Return a JSON object or raise a clear error."""
    if not isinstance(value, dict):
        raise MaasAPIError(f"{source} must be a JSON object.")
    return value


def normalize_seed(value: int | None) -> int | None:
    """Validate a MaaS seed value."""
    if value is None:
        return None
    if value < 0 or value > MAX_SEED:
        raise MaasAPIError(f"seed must be in [0, {MAX_SEED}]")
    return value


def normalize_size(value: str, *, separator: str = "x") -> str:
    """Normalize a size string such as 1024x1024 or 1024*1024."""
    size = value.strip().lower().replace("*", "x")
    parts = size.split("x")
    if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
        raise MaasAPIError(f"Invalid size: {value}")
    return f"{int(parts[0])}{separator}{int(parts[1])}"


def media_type_for_path(path: Path) -> str:
    """Return a supported image media type for a local path."""
    suffix = path.suffix.lower()
    if suffix in IMAGE_MEDIA_TYPES:
        return IMAGE_MEDIA_TYPES[suffix]
    guessed = mimetypes.guess_type(str(path))[0]
    if guessed in set(IMAGE_MEDIA_TYPES.values()):
        return guessed
    raise MaasAPIError(f"Unsupported image format for {path.name}; supported formats are png, jpeg, jpg, webp, bmp, and tiff.")


def image_reference_to_url(value: str, *, max_bytes: int | None = None) -> str:
    """Return a MaaS-compatible image URL or data URI from a local path, data URI, or HTTP URL."""
    text = value.strip()
    if not text:
        raise MaasAPIError("Image reference cannot be empty.")
    if text.startswith(("http://", "https://", "data:image/")):
        return text

    path = Path(text)
    if not path.exists() or not path.is_file():
        raise MaasAPIError(f"Image file does not exist: {text}")
    raw = path.read_bytes()
    if max_bytes is not None and len(raw) > max_bytes:
        raise MaasAPIError(f"Image file {path.name} is larger than the allowed {max_bytes} bytes.")
    media_type = media_type_for_path(path)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def build_headers(api_key: str) -> dict[str, str]:
    """Build MaaS JSON API headers."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def request_json(
    method: str,
    path: str,
    *,
    api_key: str,
    body: dict[str, Any] | None = None,
    timeout: int = 120,
    base_url: str = DEFAULT_MAAS_BASE_URL,
) -> dict[str, Any]:
    """Call a MaaS JSON API endpoint and return a structured response."""
    url = endpoint_url(path, base_url)
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=build_headers(api_key), method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        error_body = redact_maas_text(exc.read().decode("utf-8", errors="replace"), api_key)
        raise MaasAPIError(classify_http_error(exc.code, error_body)) from exc
    except urllib.error.URLError as exc:
        raise MaasAPIError(f"MaaS API network error: {exc.reason}") from exc

    if not raw_body.strip():
        parsed: Any = {}
    else:
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            redacted = redact_maas_text(raw_body[:300], api_key)
            raise MaasAPIError(f"MaaS API response was not JSON: {redacted}") from exc

    return {
        "status_code": status_code,
        "url": url,
        "body": parsed,
    }


def classify_http_error(status_code: int, body: str) -> str:
    """Return a compact, actionable MaaS HTTP error message."""
    prefix = f"MaaS API HTTP {status_code}"
    if status_code in {401, 403}:
        return f"{prefix}: API Key 未授权、未生效、区域不匹配或账号权限不足。响应摘要: {body[:300]}"
    if status_code == 429:
        return f"{prefix}: 触发限流，请降低并发或稍后重试。响应摘要: {body[:300]}"
    if 500 <= status_code <= 599:
        return f"{prefix}: 服务端错误或模型服务暂不可用。响应摘要: {body[:300]}"
    return f"{prefix}: {body[:300]}"


def response_metadata(response: dict[str, Any]) -> dict[str, Any]:
    """Return non-secret response metadata for reports."""
    body = response.get("body")
    return {
        "status_code": response.get("status_code"),
        "endpoint_host": urllib.parse.urlparse(str(response.get("url") or "")).netloc,
        "model": body.get("model") if isinstance(body, dict) else None,
        "created": body.get("created") if isinstance(body, dict) else None,
        "usage": body.get("usage") if isinstance(body, dict) else None,
    }


def summarize_payload(value: Any) -> Any:
    """Return a copy of a payload with large image data URIs summarized."""
    if isinstance(value, dict):
        return {key: summarize_payload(child) for key, child in value.items()}
    if isinstance(value, list):
        return [summarize_payload(child) for child in value]
    if isinstance(value, str) and value.startswith("data:image/") and ";base64," in value:
        header, encoded = value.split(",", 1)
        return f"{header},<base64:{len(encoded)} chars>"
    return value


def now_utc_iso() -> str:
    """Return current UTC time in manifest-friendly format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
