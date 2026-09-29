#!/usr/bin/env python3
"""
OBS Bucket Download Traffic Statistics Script

Queries OBS bucket extranet/intranet download traffic via Huawei Cloud CES (Cloud Eye Service)
and calculates the month-over-month change.

Usage:
    python3 obs_traffic_stats.py --region <Region> --bucket <BucketName> --period last_month
    python3 obs_traffic_stats.py --region <Region> --bucket <BucketName> --period this_month
    python3 obs_traffic_stats.py --region <Region> --bucket <BucketName> --from <FromDate> --to <ToDate>

Key lessons learned:
    1. You must use traffic metrics (download_traffic_extranet/download_traffic_intranet), not bandwidth metrics (download_bytes)
    2. hcloud CES dimension parameter format: --dim.0=bucket_name,<BucketName>, not the SDK dimensions format
    3. Time ranges: "this month" = calendar month (1st of month ~ now), "last 30 days" = rolling 30-day window (now - 30 days ~ now)
    4. The sum values returned by CES can be directly accumulated for total bytes; no need to multiply by the aggregation period
    5. All hcloud parameters must use the --param=value format (connected with equals sign)
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Optional


OBS_NAMESPACE = "SYS.OBS"
DAILY_PERIOD = 86400
TRAFFIC_METRICS = {
    "extranet": "download_traffic_extranet",
    "intranet": "download_traffic_intranet",
}
UPLOAD_TRAFFIC_METRICS = {
    "extranet": "upload_traffic_extranet",
    "intranet": "upload_traffic_intranet",
}
TRAFFIC_METRIC_KEYS = ["extranet", "intranet", "total"]
METRIC_ALIASES = {k.lower(): k for k in TRAFFIC_METRIC_KEYS}
REQUEST_METRICS = [
    "get_request_count",
    "put_request_count",
    "post_request_count",
    "delete_request_count",
    "head_request_count",
]


def dt_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000)


def fmt_bytes(b: float) -> str:
    if b >= 1024 ** 4:
        return f"{b / (1024 ** 4):.2f} TB"
    if b >= 1024 ** 3:
        return f"{b / (1024 ** 3):.2f} GB"
    if b >= 1024 ** 2:
        return f"{b / (1024 ** 2):.2f} MB"
    if b >= 1024:
        return f"{b / 1024:.2f} KB"
    return f"{b:.2f} Bytes"


def calc_pct(current: float, previous: float) -> str:
    if previous == 0:
        return "N/A" if current == 0 else "New (previous period was 0)"
    return f"{(current - previous) / previous * 100:+.2f}%"


def resolve_time_range(period: str, from_str: Optional[str], to_str: Optional[str]):
    now = datetime.now()
    if from_str and to_str:
        from_dt = datetime.strptime(from_str, "%Y-%m-%d")
        to_dt = datetime.strptime(to_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        duration = to_dt - from_dt
        compare_to = from_dt
        compare_from = from_dt - duration
    elif period == "this_month":
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        to_dt = now
        compare_to = from_dt - timedelta(seconds=1)
        compare_from = compare_to.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "last_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        to_dt = first_of_this_month - timedelta(seconds=1)
        from_dt = to_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        compare_to = from_dt - timedelta(seconds=1)
        compare_from = compare_to.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "last_30d":
        from_dt = now - timedelta(days=30)
        to_dt = now
        duration = to_dt - from_dt
        compare_to = from_dt
        compare_from = from_dt - duration
    else:
        raise ValueError(f"Unsupported period: {period}. Options: this_month, last_month, last_30d")

    return from_dt, to_dt, compare_from, compare_to


def validate_ces_response(resp, metric_name: str) -> dict:
    if not isinstance(resp, dict):
        raise ValueError("response is not a JSON object")
    datapoints = resp.get("datapoints", [])
    if not isinstance(datapoints, list):
        raise ValueError("datapoints is not a list")
    for dp in datapoints:
        if not isinstance(dp, dict):
            raise ValueError("datapoint is not a JSON object")
        val = dp.get("sum", 0)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or val < 0:
            raise ValueError("datapoint sum is not a non-negative number")
    return resp


class CESQueryError(Exception):
    """Raised when a CES API query returns an error response (e.g. ces.0013/ces.0015)."""
    pass


def _extract_json_object(stdout: str, metric_name: str) -> dict:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise CESQueryError(
            f"Query for {metric_name} returned non-JSON output: {stdout.strip()!r}"
        )
    try:
        return json.loads(stdout[start:end + 1])
    except json.JSONDecodeError as e:
        raise CESQueryError(
            f"Query for {metric_name} returned invalid JSON: {e}"
        )


def _check_ces_error(resp, metric_name: str):
    if not isinstance(resp, dict):
        return
    http_code = resp.get("http_code")
    if isinstance(http_code, int) and http_code != 200:
        msg = resp.get("message", {})
        code = msg.get("code", "unknown") if isinstance(msg, dict) else "unknown"
        details = msg.get("details", "") if isinstance(msg, dict) else str(msg)
        raise CESQueryError(
            f"Query for {metric_name} failed (CES error {code}, http {http_code}): {details}"
        )
    err = resp.get("error")
    if isinstance(err, dict):
        code = err.get("code", "unknown")
        details = err.get("message", "") or err.get("details", "")
        raise CESQueryError(
            f"Query for {metric_name} failed (error {code}): {details}"
        )
    error_code = resp.get("error_code")
    if isinstance(error_code, str) and error_code:
        raise CESQueryError(
            f"Query for {metric_name} failed (error {error_code}): {resp.get('error_msg', 'unknown')}"
        )
    if "datapoints" not in resp and "metric_name" not in resp:
        raise CESQueryError(
            f"Query for {metric_name} returned unexpected response: {resp}"
        )


def query_ces_metric(region: str, metric_name: str, bucket: str, from_ms: int, to_ms: int) -> dict:
    cmd = [
        "hcloud", "CES", "ShowMetricData",
        f"--region={region}",
        f"--namespace={OBS_NAMESPACE}",
        f"--metric_name={metric_name}",
        f"--dim.0=bucket_name,{bucket}",
        f"--period={DAILY_PERIOD}",
        "--filter=sum",
        f"--from={from_ms}",
        f"--to={to_ms}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except subprocess.SubprocessError as e:
        raise CESQueryError(f"Query for {metric_name} failed to execute: {e}")
    if result.returncode != 0:
        raise CESQueryError(
            f"Query for {metric_name} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    resp = _extract_json_object(result.stdout, metric_name)
    _check_ces_error(resp, metric_name)
    return validate_ces_response(resp, metric_name)


def sum_traffic(resp: dict) -> int:
    total = 0
    for dp in resp.get("datapoints", []):
        total += dp.get("sum", 0)
    return total


def query_traffic(region: str, bucket: str, from_ms: int, to_ms: int, direction: str = "download") -> dict:
    metrics = TRAFFIC_METRICS if direction == "download" else UPLOAD_TRAFFIC_METRICS
    result = {}
    has_data = False
    for key, metric_name in metrics.items():
        resp = query_ces_metric(region, metric_name, bucket, from_ms, to_ms)
        if resp.get("datapoints"):
            has_data = True
        result[key] = sum_traffic(resp)
    result["total"] = result["extranet"] + result["intranet"]
    result["has_data"] = has_data
    return result


def print_no_data_hint(bucket: str, period_label: str, from_dt: datetime, to_dt: datetime):
    print(f"Note: No monitoring data available for bucket '{bucket}' in the {period_label} "
          f"({from_dt.strftime('%Y-%m-%d')} ~ {to_dt.strftime('%Y-%m-%d')}).")
    print("      The bucket may be newly created or has no access in the selected time range.")
    print("      Please verify whether data has been written to the bucket.")


def print_traffic_report(bucket: str, cur: dict, from_dt: datetime, to_dt: datetime,
                         cmp: Optional[dict] = None,
                         compare_from: Optional[datetime] = None,
                         compare_to: Optional[datetime] = None,
                         direction: str = "Download",
                         metric_filter: Optional[list] = None):
    show_compare = cmp is not None
    if not cur.get("has_data"):
        print_no_data_hint(bucket, "current period", from_dt, to_dt)
    if show_compare and not cmp.get("has_data"):
        print_no_data_hint(bucket, "comparison period", compare_from, compare_to)
    label_map = {"extranet": "Extranet ", "intranet": "Intranet ", "total": "Total    "}
    keys_to_show = TRAFFIC_METRIC_KEYS
    if metric_filter:
        keys_to_show = [k for k in TRAFFIC_METRIC_KEYS if k in metric_filter]
    print(f"OBS {direction} Traffic Report — Bucket: {bucket}")
    print("═" * 60)
    if show_compare:
        print(f"{'Metric':<12s}{'Current Period':<20s}{'Comparison Period':<20s}{'MoM Change'}")
        print("─" * 60)
        for key in keys_to_show:
            label = f"{label_map[key]}{direction}"
            cur_val = cur[key]
            cmp_val = cmp[key]
            print(f"{label:<12s}{fmt_bytes(cur_val):<20s}{fmt_bytes(cmp_val):<20s}{calc_pct(cur_val, cmp_val)}")
    else:
        print(f"{'Metric':<12s}{'Current Period'}")
        print("─" * 60)
        for key in keys_to_show:
            label = f"{label_map[key]}{direction}"
            print(f"{label:<12s}{fmt_bytes(cur[key])}")
    print("═" * 60)
    print(f"Current Period: {from_dt.strftime('%Y-%m-%d')} ~ {to_dt.strftime('%Y-%m-%d')}")
    if show_compare:
        print(f"Comparison Period: {compare_from.strftime('%Y-%m-%d')} ~ {compare_to.strftime('%Y-%m-%d')}")


def main():
    parser = argparse.ArgumentParser(description="OBS Bucket Download Traffic Statistics")
    parser.add_argument("--region", required=True, help="Huawei Cloud region, e.g., cn-south-1")
    parser.add_argument("--bucket", required=True, help="OBS bucket name")
    parser.add_argument("--period", choices=["this_month", "last_month", "last_30d"],
                        help="Time period: this_month (this month), last_month (last month), last_30d (last 30 days)")
    parser.add_argument("--from", dest="from_str", help="Custom start date, format: YYYY-MM-DD")
    parser.add_argument("--to", dest="to_str", help="Custom end date, format: YYYY-MM-DD")
    parser.add_argument("--direction", choices=["download", "upload", "both"], default="download",
                        help="Traffic direction: download, upload, both (download + upload)")
    parser.add_argument("--compare", action="store_true",
                        help="Show comparison period and MoM change (default: disabled; enable only when the user explicitly asks for comparison/MoM)")
    parser.add_argument("--metric",
                        help=f"Comma-separated metric keys to show only specific rows. "
                             f"Supported: {','.join(TRAFFIC_METRIC_KEYS)}. "
                             f"Example: --metric intranet or --metric extranet,total")
    args = parser.parse_args()

    if not args.period and not (args.from_str and args.to_str):
        parser.error("Either --period or --from/--to must be specified")

    metric_filter = None
    if args.metric:
        requested = [m.strip() for m in args.metric.split(",") if m.strip()]
        metric_filter = []
        invalid = []
        for m in requested:
            if m.lower() in METRIC_ALIASES:
                metric_filter.append(METRIC_ALIASES[m.lower()])
            else:
                invalid.append(m)
        if invalid:
            parser.error(f"Unsupported --metric value(s): {invalid}. Supported: {TRAFFIC_METRIC_KEYS}")

    from_dt, to_dt, compare_from, compare_to = resolve_time_range(
        args.period, args.from_str, args.to_str
    )
    from_ms = dt_to_ms(from_dt)
    to_ms = dt_to_ms(to_dt)
    compare_from_ms = dt_to_ms(compare_from)
    compare_to_ms = dt_to_ms(compare_to)

    directions = []
    if args.direction in ("download", "both"):
        directions.append("download")
    if args.direction in ("upload", "both"):
        directions.append("upload")

    try:
        for d in directions:
            label = "Download" if d == "download" else "Upload"
            cur = query_traffic(args.region, args.bucket, from_ms, to_ms, direction=d)
            cmp = None
            cmp_from, cmp_to = None, None
            if args.compare:
                cmp = query_traffic(args.region, args.bucket, compare_from_ms, compare_to_ms, direction=d)
                cmp_from, cmp_to = compare_from, compare_to
            print()
            print_traffic_report(args.bucket, cur, from_dt, to_dt,
                                 cmp=cmp, compare_from=cmp_from, compare_to=cmp_to,
                                 direction=label,
                                 metric_filter=metric_filter)
    except CESQueryError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("This is a CES API error, not an empty-data condition. "
              "Check the region, bucket name, time range (from must be <= to), and IAM permissions.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
