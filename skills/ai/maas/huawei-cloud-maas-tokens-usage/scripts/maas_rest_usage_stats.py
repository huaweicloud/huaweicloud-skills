#!/usr/bin/env python3
"""
MaaS monitoring data query via Huawei Cloud SDK signing + MaaS ShowStatistics API

API doc: https://support.huaweicloud.com/api-maas/ShowStatistics.html
POST /v1/{project_id}/maas/monitoring/show-statistics

Endpoint: modelarts.{region}.myhuaweicloud.com
Auth: AK/SK signing (SDK-HMAC-SHA256), supports temporary AK/SK + Security Token
Token unit: response values are in thousands, actual = value x 1000

Environment variables:
    HW_ACCESS_KEY: Huawei Cloud AK (permanent or temporary)
    HW_SECRET_KEY: Huawei Cloud SK (permanent or temporary)
    HW_SECURITY_TOKEN: Security token (required for temporary AK/SK)

Usage:
    # Permanent AK/SK
    export HW_ACCESS_KEY=your_ak
    export HW_SECRET_KEY=your_sk
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

    # Temporary AK/SK + Security Token
    export HW_ACCESS_KEY=your_temp_ak
    export HW_SECRET_KEY=your_temp_sk
    export HW_SECURITY_TOKEN=your_security_token
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

    # Rolling window: the last 7 natural days, up to now (mutually exclusive with --from / --to)
    python3 maas_rest_usage_stats.py --last-days 7

    # POST the summary JSON to a Huawei Cloud HTTPS webhook after the query
    python3 maas_rest_usage_stats.py --last-days 7 --notify-url https://example.myhuaweicloud.com/maas-hook

    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from ipaddress import ip_address
from urllib.parse import urlparse

import requests

from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest

SERVICE_TYPE_MAP = {
    1: "My Service",
    2: "Preset Service",
    4: "Custom Endpoint",
}

# MaaS ShowStatistics is only exposed in this region (issue #112 Bug-4).
SUPPORTED_REGIONS = ("cn-southwest-2",)

# Upper bound for --last-days (10 years): keeps the date arithmetic inside the
# representable range and avoids runaway multi-segment loops.
MAX_LAST_DAYS = 3650

# Friendly labels for known numeric response fields; unmapped fields fall back
# to their raw API key (issue #112 Gap-2).
FIELD_LABELS = {
    "total_token": "Total Tokens",
    "total_prompt_token": "Prompt Tokens",
    "total_completion_token": "Completion Tokens",
    "total_request_count": "Total Requests",
    "total_error_count": "Total Errors",
    "total_completion_tasks": "Completed Batch Tasks",
    "total_infer_count": "Total Inference Count",
    "video_generate_duration": "Video Duration (s)",
    "image_generate_nums": "Generated Images",
}

# Fields rendered as fixed rows (in this order) above the "Error Rate" row.
_PRIMARY_FIELDS = (
    "total_token",
    "total_prompt_token",
    "total_completion_token",
    "total_request_count",
    "total_error_count",
)

# Remaining mapped fields, rendered right after Error Rate in FIELD_LABELS
# declaration order (contract 3.4), before any unmapped numeric field.
_EXTRA_KNOWN_FIELDS = tuple(key for key in FIELD_LABELS if key not in _PRIMARY_FIELDS)

# --notify-url is restricted to HTTPS Huawei Cloud hosts (ported from closed PR #616,
# contract 3.5): no plain HTTP, no IP literals, no third-party domains.
_TRUSTED_NOTIFY_DOMAINS = ("myhuaweicloud.com", "huaweicloud.com")


def _is_ip_literal(host):
    try:
        ip_address(host)
        return True
    except ValueError:
        return False


def _notify_url_is_allowed(url):
    """True only for https:// URLs on *.myhuaweicloud.com / *.huaweicloud.com (or the bare domains)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if _is_ip_literal(host):
        return False
    return any(host == domain or host.endswith("." + domain) for domain in _TRUSTED_NOTIFY_DOMAINS)


def _parse_credentials_file(path, ak, sk, security_token):
    """Read AK/SK/security-token from a credentials file (env values passed in win).

    Supports three mutually-exclusive formats (detected from the first line):
      KEY=VALUE, CSV three-column, and one-value-per-line.  An empty value in
      KEY=VALUE form (e.g. a bare 'HW_SECURITY_TOKEN=' line) is treated as 'no
      token' and must never fall through to the positional fallback below,
      which would otherwise send the whole line (including its KEY= text) as
      the token value and break IAM auth.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except FileNotFoundError:
        print(f"Error: Credentials file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: Cannot read credentials file {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    first = lines[0] if lines else ""
    if "=" in first:
        for line in lines:
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if not val:
                continue
            if key == "HW_ACCESS_KEY" and not ak:
                ak = val
            elif key == "HW_SECRET_KEY" and not sk:
                sk = val
            elif key == "HW_SECURITY_TOKEN" and not security_token:
                security_token = val
    elif "," in first:
        for line in lines:
            if "," not in line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if not ak and len(parts) >= 1 and parts[0]:
                ak = parts[0]
            if not sk and len(parts) >= 2 and parts[1]:
                sk = parts[1]
            if not security_token and len(parts) >= 3 and parts[2]:
                security_token = parts[2]
    else:
        if not ak and len(lines) >= 1:
            ak = lines[0]
        if not sk and len(lines) >= 2:
            sk = lines[1]
        if not security_token and len(lines) >= 3:
            security_token = lines[2]
    return ak, sk, security_token


def _send_notification(url, payload):
    """POST the summary JSON. Raises on any failure; callers must only warn."""
    resp = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        verify=True,
        timeout=10,
    )
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")


class _NetworkError(Exception):
    """Transport-level failure (DNS, TCP, TLS, timeout, proxy...) for one host."""

    def __init__(self, host, exc):
        self.host = host
        self.exc_name = type(exc).__name__
        self.exc_msg = str(exc)
        super().__init__(f"Cannot reach {host} ({self.exc_name}): {self.exc_msg}")


def _local_iana_tz():
    try:
        tz_key = datetime.now().astimezone().tzname()
        mapping = {"CST": "Asia/Shanghai", "EST": "America/New_York", "PST": "America/Los_Angeles"}
        return mapping.get(tz_key, tz_key)
    except Exception:
        return "Asia/Shanghai"


class _Creds:
    def __init__(self, ak, sk):
        self.ak = ak
        self.sk = sk


def _sign_and_request(method, host, resource_path, query_params, headers, body, ak, sk, security_token=None):
    signer = Signer(_Creds(ak, sk))
    if isinstance(body, str):
        body = body.encode("utf-8")
    elif body is None:
        body = b""

    # Add security token header for temporary credentials
    if security_token:
        headers = dict(headers)
        headers["X-Security-Token"] = security_token

    req = SdkRequest(
        method=method,
        schema="https",
        host=host,
        resource_path=resource_path,
        uri=resource_path,
        query_params=query_params or [],
        header_params=headers,
        body=body,
    )
    signed_req = signer.sign(req)

    req_headers = {}
    for k, v in signed_req.header_params.items():
        req_headers[k] = v

    url = f"https://{host}{signed_req.uri}"
    try:
        return requests.request(method, url, headers=req_headers, data=body, verify=True, timeout=30)
    except (requests.exceptions.RequestException, OSError) as exc:
        # Never surface a raw traceback for connectivity problems.
        raise _NetworkError(host, exc) from exc


def _parse_json_response(resp, context):
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON response from {context}: {exc}") from exc


def get_project_id(ak, sk, region, security_token=None):
    iam_host = f"iam.{region}.myhuaweicloud.com"
    resp = _sign_and_request(
        "GET", iam_host, "/v3/projects", [("name", region)],
        {"Content-Type": "application/json"}, None, ak, sk, security_token,
    )
    if resp.status_code == 200:
        projects = _parse_json_response(resp, iam_host).get("projects", [])
        if projects:
            return projects[0]["id"]
    raise RuntimeError(f"Failed to get project_id: {resp.status_code} {resp.text[:300]}")


def show_statistics(endpoint, project_id, ak, sk, body, security_token=None):
    resource_path = f"/v1/{project_id}/maas/monitoring/show-statistics"
    body_bytes = json.dumps(body).encode("utf-8")
    resp = _sign_and_request(
        "POST", endpoint, resource_path, [],
        {"Content-Type": "application/json"}, body_bytes, ak, sk, security_token,
    )
    if resp.status_code == 200:
        payload = _parse_json_response(resp, endpoint)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected ShowStatistics response type: {type(payload).__name__}")
        return payload
    raise RuntimeError(f"ShowStatistics failed: {resp.status_code} {resp.text[:500]}")


def fmt_tokens(val_k):
    val_m = val_k / 1000
    if val_m >= 1:
        return f"{val_m:,.2f} M tokens"
    return f"{val_k:,.2f} K tokens"


def _parse_date(value, label):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid {label} date format: '{value}'", file=sys.stderr)
        print("       Date format should be YYYY-MM-DD, e.g. 2026-08-10", file=sys.stderr)
        sys.exit(1)


def _is_number(value):
    """True only for int/float (bool is explicitly excluded)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _fmt_count(value):
    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
            return f"{value:,.2f}"
    return f"{value:,}"


def _fmt_extra(field, value):
    if "token" in field.lower():
        return fmt_tokens(value)
    return _fmt_count(value)


def main():
    parser = argparse.ArgumentParser(description="MaaS usage statistics via ShowStatistics API")
    parser.add_argument("--region", default="cn-southwest-2",
                        help="Region (default: cn-southwest-2; only cn-southwest-2 is supported)")
    parser.add_argument("--from", dest="from_date",
                        help="Start date YYYY-MM-DD (required unless --last-days is used)")
    parser.add_argument("--to", dest="to_date",
                        help="End date YYYY-MM-DD (required unless --last-days is used)")
    parser.add_argument("--last-days",
                        help="Rolling window of the last N natural days up to now "
                             "(integer 1-3650, mutually exclusive with --from/--to)")
    parser.add_argument("--notify-url",
                        help="POST the summary JSON to this HTTPS Huawei Cloud webhook "
                             "(*.myhuaweicloud.com / *.huaweicloud.com)")
    parser.add_argument("--service-type", type=int, default=2,
                        help="Service type: 1=My Service, 2=Preset Service(default), 4=Custom Endpoint")
    parser.add_argument("--infer-type", default="real_time", help="Infer type: real_time(default), batch")
    parser.add_argument("--api-keys", nargs="*", help="Filter by API Key list")
    parser.add_argument("--raw", action="store_true", help="Show raw API response")
    parser.add_argument("--credentials-file", help="Credentials file path (KEY=VALUE, CSV, or one-per-line)")
    args = parser.parse_args()

    # ---- Parameter validation (must run before any credential lookup) ----
    last_days = None
    if args.last_days is not None:
        if args.from_date is not None or args.to_date is not None:
            print("Error: --last-days cannot be combined with --from / --to.", file=sys.stderr)
            sys.exit(1)
        try:
            last_days = int(str(args.last_days).strip())
        except ValueError:
            last_days = None
        if last_days is None or last_days < 1:
            print(f"Error: --last-days must be a positive integer, got '{args.last_days}'.", file=sys.stderr)
            sys.exit(1)
        if last_days > MAX_LAST_DAYS:
            print(f"Error: --last-days must not exceed {MAX_LAST_DAYS} days, got '{args.last_days}'.", file=sys.stderr)
            sys.exit(1)
    elif args.from_date is None or args.to_date is None:
        print("Error: --from and --to are required unless --last-days is used.", file=sys.stderr)
        sys.exit(1)

    local_tz = datetime.now().astimezone().tzinfo
    if last_days is not None:
        # Last N natural days: from = today-(N-1) at 00:00 local, to = now local.
        # The MAX_LAST_DAYS check above already bounds N; this is a defensive guard
        # so no arithmetic overflow can ever surface as a bare traceback.
        try:
            now_local = datetime.now().astimezone()
            to_dt = now_local
            from_dt = (now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                       - timedelta(days=last_days - 1))
        except (OverflowError, ValueError, OSError) as exc:
            print(f"Error: --last-days date window is out of range "
                  f"({type(exc).__name__}): {exc}", file=sys.stderr)
            print("       Use a smaller --last-days value or an explicit --from/--to range.",
                  file=sys.stderr)
            sys.exit(1)
    else:
        from_dt = _parse_date(args.from_date, "--from").replace(tzinfo=local_tz)
        to_dt = _parse_date(args.to_date, "--to").replace(tzinfo=local_tz)

    if from_dt > to_dt:
        from_label = args.from_date if args.from_date is not None else from_dt.strftime("%Y-%m-%d")
        to_label = args.to_date if args.to_date is not None else to_dt.strftime("%Y-%m-%d")
        print(f"Error: --from ({from_label}) must not be later than --to ({to_label}).", file=sys.stderr)
        sys.exit(1)

    region = args.region
    if region not in SUPPORTED_REGIONS:
        print(f"Error: Unsupported region '{region}'. "
              f"MaaS ShowStatistics only supports: cn-southwest-2.", file=sys.stderr)
        sys.exit(1)

    if args.notify_url is not None and not _notify_url_is_allowed(args.notify_url):
        print("Error: --notify-url rejected: only HTTPS URLs on trusted Huawei Cloud hosts "
              "(*.myhuaweicloud.com / *.huaweicloud.com) are allowed; the request was NOT sent.",
              file=sys.stderr)
        sys.exit(1)

    # ---- Credentials (env first, then --credentials-file) ----
    ak = os.environ.get("HW_ACCESS_KEY", "")
    sk = os.environ.get("HW_SECRET_KEY", "")
    security_token = os.environ.get("HW_SECURITY_TOKEN", "")

    if (not ak or not sk) and args.credentials_file:
        ak, sk, security_token = _parse_credentials_file(
            args.credentials_file, ak, sk, security_token)

    if not ak or not sk:
        print("Error: Credentials not found. Provide AK/SK via:", file=sys.stderr)
        print("  1. Environment variables: export HW_ACCESS_KEY=xxx && export HW_SECRET_KEY=xxx", file=sys.stderr)
        print("     For temporary credentials: also export HW_SECURITY_TOKEN=xxx", file=sys.stderr)
        print("  2. Credentials file: --credentials-file <path>", file=sys.stderr)
        sys.exit(1)

    endpoint = f"modelarts.{region}.myhuaweicloud.com"
    svc_name = SERVICE_TYPE_MAP.get(args.service_type, str(args.service_type))

    base_body = {
        "service_type": args.service_type,
        "timezone": _local_iana_tz(),
        "infer_type": args.infer_type,
    }
    if args.api_keys is not None:
        base_body["api_keys"] = args.api_keys

    max_days = 29
    delta_days = (to_dt - from_dt).days
    segments = []
    if delta_days <= max_days:
        segments.append((from_dt, to_dt))
    else:
        cur = from_dt
        while cur < to_dt:
            seg_end = min(cur + timedelta(days=max_days), to_dt)
            segments.append((cur, seg_end))
            cur = seg_end

    totals = {key: 0 for key in _PRIMARY_FIELDS}
    extra_totals = {}
    seen_keys = set()
    raw_responses = []

    try:
        project_id = get_project_id(ak, sk, region, security_token)

        for seg_from, seg_to in segments:
            body = dict(base_body)
            body["start_time"] = int(seg_from.timestamp() * 1000)
            body["end_time"] = int(seg_to.timestamp() * 1000)
            data = show_statistics(endpoint, project_id, ak, sk, body, security_token)
            for key, value in data.items():
                seen_keys.add(key)
                if not _is_number(value):
                    # Non-numeric keys (strings, objects, null, bool) are ignored.
                    continue
                if key in totals:
                    totals[key] += value
                else:
                    extra_totals[key] = extra_totals.get(key, 0) + value
            if args.raw:
                raw_responses.append({
                    "segment": f"{seg_from.strftime('%Y-%m-%d')}~{seg_to.strftime('%Y-%m-%d')}",
                    "data": data,
                })
    except _NetworkError as exc:
        print(f"Error: Cannot reach {exc.host} ({exc.exc_name}): {exc.exc_msg}", file=sys.stderr)
        print("       Check --region, network connectivity, proxy/firewall settings, "
              "and that credentials are valid.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("       Check the request parameters, region, and credential permissions "
              "(401/403 = credentials/IAM).", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # never leak a bare traceback
        print(f"Error: {exc}", file=sys.stderr)
        print("       Check the request parameters, region, and credential permissions "
              "(401/403 = credentials/IAM).", file=sys.stderr)
        sys.exit(1)

    total_req = totals["total_request_count"]
    total_err = totals["total_error_count"]
    total_token = totals["total_token"]
    prompt_token = totals["total_prompt_token"]
    completion_token = totals["total_completion_token"]

    error_rate = total_err / total_req * 100 if total_req > 0 else 0
    tz_label = datetime.now().astimezone().strftime("%Z")
    time_range = (f"{from_dt.strftime('%Y-%m-%d %H:%M:%S')} ~ "
                  f"{to_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_label})")

    # Row order is fixed by contract 3.4. The five core metrics and Error Rate are
    # always shown; mapped/unmapped extra fields only when the API returned the key
    # in at least one segment (never fabricate a zero row).
    rows = [
        ("Total Tokens", fmt_tokens(total_token)),
        ("Prompt Tokens", fmt_tokens(prompt_token)),
        ("Completion Tokens", fmt_tokens(completion_token)),
        ("Total Requests", f"{total_req:,}"),
        ("Total Errors", f"{total_err:,}"),
        ("Error Rate", f"{error_rate:.2f}%"),
    ]
    for field in _EXTRA_KNOWN_FIELDS:
        if field in seen_keys:
            rows.append((FIELD_LABELS[field], _fmt_extra(field, extra_totals.get(field, 0))))
    for field in sorted(key for key in extra_totals if key not in FIELD_LABELS):
        rows.append((field, _fmt_extra(field, extra_totals[field])))

    # Adaptive widths: no label/value may push the right border out of line.
    col1_w = max(20, max(len(label) for label, _ in rows))
    col2_w = max(22, max(len(value) for _, value in rows))
    sep = f"+{'─'*col1_w}+{'─'*col2_w}+"
    row_fmt = f"| {{:<{col1_w}}} | {{:<{col2_w}}} |"

    print()
    print(f"MaaS {svc_name} Usage Statistics - Region: {region}")
    print(sep)
    print(row_fmt.format("Metric", "Value"))
    print(sep.replace("─", "═"))
    for label, value in rows:
        print(row_fmt.format(label, value))
    print(sep)
    print(f"Period: {time_range}")

    if total_req == 0 and total_token == 0:
        print("Note: no usage data in this period (all values are zero). "
              "Verify the time range, service type, infer type, and API key filter.")
        print("Note: if --from equals --to, the query window is a single instant "
              "(00:00-00:00); use a wider range or --last-days.")

    if args.raw:
        print(f"\nRaw API Response:")
        print(json.dumps(raw_responses, indent=2, ensure_ascii=False))

    if args.notify_url is not None:
        payload = {
            "region": region,
            "period": time_range,
            "total_tokens": total_token,
            "prompt_tokens": prompt_token,
            "completion_tokens": completion_token,
            "total_requests": total_req,
            "total_errors": total_err,
        }
        try:
            _send_notification(args.notify_url, payload)
            print(f"Results sent to webhook: {args.notify_url}")
        except Exception as exc:
            # A failed notification must never change the exit code of the query.
            print(f"Warning: failed to send --notify-url notification: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
