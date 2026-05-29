#!/usr/bin/env python3
"""
MaaS monitoring data query via Huawei Cloud SDK signing + MaaS ShowStatistics API

API doc: https://support.huaweicloud.com/api-maas/ShowStatistics.html
POST /v1/{project_id}/maas/monitoring/show-statistics

Endpoint: modelarts.{region}.myhuaweicloud.com
Auth: AK/SK signing (SDK-HMAC-SHA256)
Token unit: response values are in thousands, actual = value x 1000

Environment variables:
    HW_ACCESS_KEY: Huawei Cloud AK
    HW_SECRET_KEY: Huawei Cloud SK

Usage:
    export HW_ACCESS_KEY=your_ak
    export HW_SECRET_KEY=your_sk
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4
    python3 maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests
import urllib3

from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVICE_TYPE_MAP = {
    1: "My Service",
    2: "Preset Service",
    4: "Custom Endpoint",
}


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


def _sign_and_request(method, host, resource_path, query_params, headers, body, ak, sk):
    signer = Signer(_Creds(ak, sk))
    if isinstance(body, str):
        body = body.encode("utf-8")
    elif body is None:
        body = b""

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
    return requests.request(method, url, headers=req_headers, data=body, verify=False, timeout=30)


def get_project_id(ak, sk, region):
    iam_host = f"iam.{region}.myhuaweicloud.com"
    resp = _sign_and_request(
        "GET", iam_host, "/v3/projects", [("name", region)],
        {"Content-Type": "application/json"}, None, ak, sk,
    )
    if resp.status_code == 200:
        projects = resp.json().get("projects", [])
        if projects:
            return projects[0]["id"]
    raise RuntimeError(f"Failed to get project_id: {resp.status_code} {resp.text[:300]}")


def show_statistics(endpoint, project_id, ak, sk, body):
    resource_path = f"/v1/{project_id}/maas/monitoring/show-statistics"
    body_bytes = json.dumps(body).encode("utf-8")
    resp = _sign_and_request(
        "POST", endpoint, resource_path, [],
        {"Content-Type": "application/json"}, body_bytes, ak, sk,
    )
    if resp.status_code == 200:
        return resp.json()
    raise RuntimeError(f"ShowStatistics failed: {resp.status_code} {resp.text[:500]}")


def fmt_tokens(val_k):
    val_m = val_k / 1000
    if val_m >= 1:
        return f"{val_m:,.2f} M tokens"
    return f"{val_k:,.2f} K tokens"


def main():
    parser = argparse.ArgumentParser(description="MaaS usage statistics via ShowStatistics API")
    parser.add_argument("--region", default="cn-southwest-2", help="Region (default: cn-southwest-2)")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--service-type", type=int, default=2,
                        help="Service type: 1=My Service, 2=Preset Service(default), 4=Custom Endpoint")
    parser.add_argument("--infer-type", default="real_time", help="Infer type: real_time(default), batch")
    parser.add_argument("--api-keys", nargs="*", help="Filter by API Key list")
    parser.add_argument("--raw", action="store_true", help="Show raw API response")
    parser.add_argument("--credentials-file", help="Credentials file path (KEY=VALUE, CSV, or one-per-line)")
    args = parser.parse_args()

    ak = os.environ.get("HW_ACCESS_KEY", "")
    sk = os.environ.get("HW_SECRET_KEY", "")

    if (not ak or not sk) and args.credentials_file:
        try:
            with open(args.credentials_file, "r") as f:
                lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            for line in lines:
                if "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key == "HW_ACCESS_KEY" and not ak:
                        ak = val
                    elif key == "HW_SECRET_KEY" and not sk:
                        sk = val
                elif "," in line:
                    parts = [p.strip() for p in line.split(",")]
                    if not ak and len(parts) >= 1:
                        ak = parts[0]
                    if not sk and len(parts) >= 2:
                        sk = parts[1]
            if not ak and len(lines) >= 1:
                ak = lines[0]
            if not sk and len(lines) >= 2:
                sk = lines[1]
        except FileNotFoundError:
            print(f"Error: Credentials file not found: {args.credentials_file}", file=sys.stderr)
            sys.exit(1)

    if not ak or not sk:
        print("Error: Credentials not found. Provide AK/SK via:", file=sys.stderr)
        print("  1. Environment variables: export HW_ACCESS_KEY=xxx && export HW_SECRET_KEY=xxx", file=sys.stderr)
        print("  2. Credentials file: --credentials-file <path>", file=sys.stderr)
        sys.exit(1)

    region = args.region
    endpoint = f"modelarts.{region}.myhuaweicloud.com"

    local_tz = datetime.now().astimezone().tzinfo
    from_dt = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=local_tz)
    to_dt = datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=local_tz)

    project_id = get_project_id(ak, sk, region)

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

    total_req = 0
    total_err = 0
    total_token = 0.0
    prompt_token = 0.0
    completion_token = 0.0
    raw_responses = []

    for seg_from, seg_to in segments:
        body = dict(base_body)
        body["start_time"] = int(seg_from.timestamp() * 1000)
        body["end_time"] = int(seg_to.timestamp() * 1000)
        data = show_statistics(endpoint, project_id, ak, sk, body)
        total_req += data.get("total_request_count", 0)
        total_err += data.get("total_error_count", 0)
        total_token += data.get("total_token", 0)
        prompt_token += data.get("total_prompt_token", 0)
        completion_token += data.get("total_completion_token", 0)
        if args.raw:
            raw_responses.append({"segment": f"{seg_from.strftime('%Y-%m-%d')}~{seg_to.strftime('%Y-%m-%d')}", "data": data})

    fail_rate = total_err / total_req * 100 if total_req > 0 else 0
    tz_label = datetime.now().astimezone().strftime("%Z")
    time_range = f"{from_dt.strftime('%Y-%m-%d 00:00:00')} ~ {to_dt.strftime('%Y-%m-%d 00:00:00')} ({tz_label})"

    col1_w = 20
    col2_w = 22
    sep = f"+{'─'*col1_w}+{'─'*col2_w}+"
    row_fmt = f"| {{:<{col1_w}}} | {{:<{col2_w}}} |"

    print()
    print(f"MaaS {svc_name} Usage Statistics - Region: {region}")
    print(sep)
    print(row_fmt.format("Metric", "Value"))
    print(sep.replace("─", "═"))
    print(row_fmt.format("Total Tokens", fmt_tokens(total_token)))
    print(row_fmt.format("Prompt Tokens", fmt_tokens(prompt_token)))
    print(row_fmt.format("Completion Tokens", fmt_tokens(completion_token)))
    print(row_fmt.format("Total Requests", f"{total_req:,}"))
    print(row_fmt.format("Total Errors", f"{total_err:,}"))
    print(row_fmt.format("Error Rate", f"{fail_rate:.2f}%"))
    print(sep)
    print(f"Period: {time_range}")

    if args.raw:
        print(f"\nRaw API Response:")
        print(json.dumps(raw_responses, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
