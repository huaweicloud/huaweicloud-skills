#!/usr/bin/env python3
"""Build a dry-run request plan for Huawei Cloud MaaS usage statistics."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import credential_aliases
import hcloud_common

DEFAULT_REGION = "cn-southwest-2"
SERVICE_TYPES = {
    "my-service": 1,
    "preset-service": 2,
    "custom-endpoint": 4,
}
INFER_TYPES = ("real_time", "batch")
PRESETS = ("last-7-days", "last-14-days", "last-30-days", "this-month")
CREDENTIAL_ENV_KEYS = credential_aliases.ALL_CREDENTIAL_ENV_NAMES
ACCESS_KEY_ENV_KEYS = credential_aliases.CLOUD_ACCESS_KEY_ENV_NAMES
SECRET_KEY_ENV_KEYS = credential_aliases.CLOUD_SECRET_KEY_ENV_NAMES
PROJECT_ID_ENV_KEYS = credential_aliases.PROJECT_ID_ENV_NAMES
SECURITY_TOKEN_ENV_KEYS = credential_aliases.SECURITY_TOKEN_ENV_NAMES
ALGORITHM = "SDK-HMAC-SHA256"


class MaasUsagePlanError(ValueError):
    """Raised when a MaaS usage request plan cannot be built."""


@dataclass(frozen=True)
class DateRange:
    """Normalized MaaS statistics date range."""

    start: date
    end: date
    source: str

    @property
    def days(self) -> int:
        """Return the number of calendar days in the range."""
        return (self.end - self.start).days


def utc_midnight_ms(value: date) -> int:
    """Return the UTC midnight timestamp in milliseconds for a date."""
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1000)


def env_presence(keys: tuple[str, ...] = CREDENTIAL_ENV_KEYS) -> dict[str, dict[str, bool]]:
    """Return redacted credential environment presence."""
    return credential_aliases.credential_environment_presence(keys)


def first_env_value(keys: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Return the first non-empty environment value and its variable name."""
    return credential_aliases.resolve_first_value(keys)


def resolve_credentials() -> dict[str, Any]:
    """Resolve redacted AK/SK/project credential aliases for MaaS usage execution."""
    cloud = credential_aliases.resolve_cloud_credentials()
    access_key = cloud["access_key"]
    secret_key = cloud["secret_key"]
    project_id, project_id_source = first_env_value(PROJECT_ID_ENV_KEYS)
    security_token = cloud["security_token"]
    sources = cloud["sources"]
    return {
        "access_key": access_key,
        "secret_key": secret_key,
        "project_id": project_id,
        "security_token": security_token,
        "sources": {
            "access_key": sources["access_key"],
            "secret_key": sources["secret_key"],
            "project_id": project_id_source,
            "security_token": sources["security_token"],
            "credential_family": cloud["family"],
        },
        "presence": {
            "access_key": bool(access_key),
            "secret_key": bool(secret_key),
            "project_id": bool(project_id),
            "security_token": bool(security_token),
        },
    }


def redact_credential_resolution(credentials: dict[str, Any]) -> dict[str, Any]:
    """Return credential source metadata without credential values."""
    return {
        "presence": credentials["presence"],
        "sources": credentials["sources"],
        "secrets_printed": False,
        "redaction": hcloud_common.redaction_metadata(),
    }


def parse_date(value: str, name: str) -> date:
    """Parse a YYYY-MM-DD date string."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise MaasUsagePlanError(f"{name} must use YYYY-MM-DD format: {value}") from exc


def resolve_date_range(args: argparse.Namespace, *, today: date | None = None) -> DateRange:
    """Resolve explicit or preset MaaS usage date ranges."""
    today = today or date.today()
    if args.start_date or args.end_date:
        if not args.start_date or not args.end_date:
            raise MaasUsagePlanError("--from and --to must be provided together.")
        date_range = DateRange(
            start=parse_date(args.start_date, "--from"),
            end=parse_date(args.end_date, "--to"),
            source="explicit",
        )
    elif args.preset == "this-month":
        date_range = DateRange(start=today.replace(day=1), end=today, source=args.preset)
    else:
        days = {
            "last-7-days": 7,
            "last-14-days": 14,
            "last-30-days": 30,
        }[args.preset]
        date_range = DateRange(start=today - timedelta(days=days), end=today, source=args.preset)

    if date_range.end <= date_range.start:
        raise MaasUsagePlanError("The end date must be later than the start date.")
    return date_range


def build_warnings(args: argparse.Namespace, date_range: DateRange, *, today: date | None = None) -> list[str]:
    """Return request planning warnings."""
    today = today or date.today()
    warnings: list[str] = []
    if args.region != DEFAULT_REGION:
        warnings.append("MaaS ShowStatistics is expected to be available only in cn-southwest-2; verify region support before execution.")
    if date_range.days > 30:
        warnings.append("The requested range is longer than 30 days; split into 30-day windows and aggregate results.")
    if date_range.start < today - timedelta(days=30):
        warnings.append("MaaS statistics are documented as retaining roughly 30 days of data; older data may be unavailable.")
    if args.service_type == "custom-endpoint":
        warnings.append("Custom endpoint statistics use service_type=4; do not use service_type=3.")
    return warnings


def sha256_hex(data: bytes) -> str:
    """Return a SHA256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def url_encode(value: str) -> str:
    """URL-encode one canonical request component."""
    return quote(value, safe="~")


def canonical_uri(path: str) -> str:
    """Return a Huawei SDK-compatible canonical URI."""
    encoded = "/".join(url_encode(part) for part in path.split("/"))
    return encoded if encoded.endswith("/") else f"{encoded}/"


def canonical_headers(headers: dict[str, str], signed_headers: list[str]) -> str:
    """Return canonical headers for Huawei AK/SK signing."""
    lowered = {key.lower(): str(value).strip() for key, value in headers.items()}
    return "".join(f"{key}:{lowered[key]}\n" for key in signed_headers)


def sign_headers(
    *,
    method: str,
    host: str,
    path: str,
    body: bytes,
    access_key: str,
    secret_key: str,
    project_id: str,
    security_token: str | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    """Build signed Huawei AK/SK headers for the MaaS usage request."""
    request_time = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    headers = {
        "Content-Type": "application/json",
        "Host": host,
        "X-Project-Id": project_id,
        "X-Sdk-Date": request_time,
    }
    if security_token:
        headers["X-Security-Token"] = security_token
    signed_headers = sorted(key.lower() for key in headers if "_" not in key)
    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri(path),
            "",
            canonical_headers(headers, signed_headers),
            ";".join(signed_headers),
            sha256_hex(body),
        ]
    )
    string_to_sign = "\n".join([ALGORITHM, request_time, sha256_hex(canonical_request.encode("utf-8"))])
    signature = hmac.new(secret_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    headers["Authorization"] = f"{ALGORITHM} Access={access_key}, SignedHeaders={';'.join(signed_headers)}, Signature={signature}"
    return headers


def summarize_usage_response(payload: Any) -> dict[str, Any]:
    """Return a compact MaaS usage response summary without account identifiers."""
    if not isinstance(payload, dict):
        return {"json_type": type(payload).__name__}
    summary: dict[str, Any] = {
        "top_level_keys": sorted(payload.keys()),
        "record_count": 0,
        "usage_field_presence": {},
    }
    candidate_records = []
    for value in payload.values():
        if isinstance(value, list):
            candidate_records.extend(item for item in value if isinstance(item, dict))
    summary["record_count"] = len(candidate_records)
    fields = [
        "total_token",
        "total_prompt_token",
        "total_completion_token",
        "total_request_count",
        "total_error_count",
    ]
    summary["usage_field_presence"] = {field: any(field in item for item in candidate_records) or field in payload for field in fields}
    return summary


def execute_usage_request(plan: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    """Execute the read-only MaaS usage statistics request with AK/SK signing."""
    credentials = resolve_credentials()
    missing = [
        name for name, present in credentials["presence"].items() if name in {"access_key", "secret_key", "project_id"} and not present
    ]
    if missing:
        return {
            "execution_success": False,
            "status": "blocked",
            "missing_credentials": missing,
            "credential_resolution": redact_credential_resolution(credentials),
            "secrets_printed": False,
        }

    region = plan["region"]
    method = plan["method"]
    host = f"modelarts.{region}.myhuaweicloud.com"
    path = f"/v1/{credentials['project_id']}/maas/monitoring/show-statistics"
    body = json.dumps(plan["request_body"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = sign_headers(
        method=method,
        host=host,
        path=path,
        body=body,
        access_key=credentials["access_key"],
        secret_key=credentials["secret_key"],
        project_id=credentials["project_id"],
        security_token=credentials.get("security_token"),
    )
    request = Request(f"https://{host}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            status_code = response.status
            response_headers = dict(response.headers.items())
    except HTTPError as exc:
        response_body = exc.read()
        status_code = exc.code
        response_headers = dict(exc.headers.items())
    except URLError as exc:
        return {
            "execution_success": False,
            "status": "network_error",
            "error": str(exc.reason),
            "credential_resolution": redact_credential_resolution(credentials),
            "signed_header_names": sorted(key for key in headers if key != "Authorization"),
            "secrets_printed": False,
        }

    text = response_body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text) if text else None
    except json.JSONDecodeError:
        parsed = None
    success = 200 <= status_code < 300
    return {
        "execution_success": success,
        "status": "ok" if success else "http_error",
        "status_code": status_code,
        "response_content_type": response_headers.get("Content-Type") or response_headers.get("content-type"),
        "request_id_present": bool(response_headers.get("X-Request-Id") or response_headers.get("x-request-id")),
        "response_summary": summarize_usage_response(parsed),
        "error_code": parsed.get("error_code") if isinstance(parsed, dict) else None,
        "error_msg": parsed.get("error_msg") if isinstance(parsed, dict) else None,
        "credential_resolution": redact_credential_resolution(credentials),
        "signed_header_names": sorted(key for key in headers if key != "Authorization"),
        "secrets_printed": False,
    }


def build_plan(args: argparse.Namespace, *, today: date | None = None) -> dict[str, Any]:
    """Build a non-executing MaaS usage statistics request plan."""
    today = today or date.today()
    date_range = resolve_date_range(args, today=today)
    service_type = SERVICE_TYPES[args.service_type]
    body = {
        "service_type": service_type,
        "infer_type": args.infer_type,
        "start_time": utc_midnight_ms(date_range.start),
        "end_time": utc_midnight_ms(date_range.end),
    }
    plan = {
        "success": True,
        "dry_run": not args.execute,
        "method": "POST",
        "endpoint": f"https://modelarts.{args.region}.myhuaweicloud.com/v1/{{project_id}}/maas/monitoring/show-statistics",
        "region": args.region,
        "date_range": {
            "from": date_range.start.isoformat(),
            "to": date_range.end.isoformat(),
            "days": date_range.days,
            "source": date_range.source,
        },
        "auth": {
            "mode": "AK/SK signing",
            "credential_presence": env_presence(),
            "secrets_printed": False,
            "note": "Do not paste AK/SK into chat. Configure credentials locally through environment variables or an hcloud profile-derived workflow.",
        },
        "credential_resolution": redact_credential_resolution(resolve_credentials()),
        "request_body": body,
        "required_permissions": [
            "modelarts:monitoring:get",
            "modelarts:service:get",
            "iam:projects:get",
        ],
        "response_notes": {
            "usage_fields": [
                "total_token",
                "total_prompt_token",
                "total_completion_token",
                "total_request_count",
                "total_error_count",
            ],
            "time_unit": "start_time and end_time are UTC millisecond timestamps.",
            "token_unit": "Returned token values are in thousands; multiply by 1000 before reporting actual token counts.",
            "error_rate": "total_error_count / total_request_count, when total_request_count is greater than zero.",
        },
        "warnings": build_warnings(args, date_range, today=today),
        "execution_boundary": "Default mode does not sign requests or call MaaS APIs. --execute performs a read-only MaaS ShowStatistics request and still does not print credential values.",
    }
    if args.execute:
        plan["execution"] = execute_usage_request(plan, timeout=args.timeout)
        plan["success"] = bool(plan["execution"].get("execution_success"))
    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start_date", help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="end_date", help="End date in YYYY-MM-DD format.")
    parser.add_argument("--preset", choices=PRESETS, default="last-7-days", help="Date preset used when --from/--to are omitted.")
    parser.add_argument("--region", default=DEFAULT_REGION, help="MaaS statistics region.")
    parser.add_argument("--service-type", choices=tuple(SERVICE_TYPES), default="preset-service", help="MaaS service type to query.")
    parser.add_argument("--infer-type", choices=INFER_TYPES, default="real_time", help="Inference type.")
    parser.add_argument("--execute", action="store_true", help="Execute the read-only MaaS ShowStatistics request with AK/SK signing.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for --execute MaaS request.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    try:
        result = build_plan(args)
    except MaasUsagePlanError as exc:
        hcloud_common.emit_json({"success": False, "error": str(exc)}, pretty=args.pretty)
        return 2
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
