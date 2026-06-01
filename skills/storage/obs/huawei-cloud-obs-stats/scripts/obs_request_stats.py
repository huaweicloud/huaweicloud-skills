#!/usr/bin/env python3
"""
OBS Bucket Total Request Statistics Script

Queries OBS bucket request counts by type via Huawei Cloud CES (Cloud Eye Service),
sums the total requests, and calculates the month-over-month change.

Usage:
    python3 obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period last_30d
    python3 obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month
    python3 obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20

Key lessons learned:
    1. OBS has no single request_count metric; you must query get/put/post/delete/head_request_count separately and sum them
    2. hcloud CES dimension parameter format: --dim.0=bucket_name,<BucketName>, not the SDK dimensions format
    3. Time ranges: "this month" = calendar month (1st of month ~ now), "last 30 days" = rolling 30-day window (now - 30 days ~ now)
    4. The sum values returned by CES can be directly accumulated for total request count; no conversion needed
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
REQUEST_METRICS = {
    "GET": "get_request_count",
    "PUT": "put_request_count",
    "POST": "post_request_count",
    "DELETE": "delete_request_count",
    "HEAD": "head_request_count",
}
ERROR_METRICS = {
    "4xx": "request_count_4xx",
    "5xx": "request_count_5xx",
}


def dt_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f} M"
    if n >= 1_000:
        return f"{n / 1_000:.2f} K"
    return str(n)


def calc_pct(current: float, previous: float) -> str:
    if previous == 0:
        return "N/A" if current == 0 else "New (previous period was 0)"
    return f"{(current - previous) / previous * 100:+.2f}%"


def resolve_time_range(period: str, from_str: Optional[str], to_str: Optional[str]):
    now = datetime.now()
    if from_str and to_str:
        from_dt = datetime.strptime(from_str, "%Y-%m-%d")
        to_dt = datetime.strptime(to_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
    elif period == "this_month":
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        to_dt = now
    elif period == "last_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        to_dt = first_of_this_month - timedelta(seconds=1)
        from_dt = to_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "last_30d":
        from_dt = now - timedelta(days=30)
        to_dt = now
    else:
        raise ValueError(f"Unsupported period: {period}. Options: this_month, last_month, last_30d")

    duration = to_dt - from_dt
    compare_to = from_dt
    compare_from = from_dt - duration

    return from_dt, to_dt, compare_from, compare_to


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: Query for {metric_name} failed: {result.stderr.strip()}", file=sys.stderr)
        return {"datapoints": [], "metric_name": metric_name}
    return json.loads(result.stdout)


def sum_metric(resp: dict) -> int:
    total = 0
    for dp in resp.get("datapoints", []):
        total += dp.get("sum", 0)
    return int(total)


def query_requests(region: str, bucket: str, from_ms: int, to_ms: int,
                   include_errors: bool = False) -> dict:
    result = {}
    total = 0
    for label, metric_name in REQUEST_METRICS.items():
        resp = query_ces_metric(region, metric_name, bucket, from_ms, to_ms)
        val = sum_metric(resp)
        result[label] = val
        total += val
    result["total"] = total

    if include_errors:
        for label, metric_name in ERROR_METRICS.items():
            resp = query_ces_metric(region, metric_name, bucket, from_ms, to_ms)
            result[label] = sum_metric(resp)

    return result


def print_request_report(bucket: str, cur: dict, cmp: dict,
                         from_dt: datetime, to_dt: datetime,
                         compare_from: datetime, compare_to: datetime,
                         include_errors: bool = False):
    rows = [("Total Requests", "total")] + [(f"{k} Requests", k) for k in REQUEST_METRICS.keys()]
    if include_errors:
        rows += [(f"{k} Status Codes", k) for k in ERROR_METRICS.keys()]

    print(f"OBS Request Report — Bucket: {bucket}")
    print("═" * 64)
    print(f"{'Metric':<14s}{'Current Period':<20s}{'Comparison Period':<20s}{'MoM Change'}")
    print("─" * 64)
    for label, key in rows:
        cur_val = cur[key]
        cmp_val = cmp[key]
        print(f"{label:<14s}{fmt_count(cur_val):<20s}{fmt_count(cmp_val):<20s}{calc_pct(cur_val, cmp_val)}")
    print("═" * 64)
    print(f"Current Period: {from_dt.strftime('%Y-%m-%d')} ~ {to_dt.strftime('%Y-%m-%d')}")
    print(f"Comparison Period: {compare_from.strftime('%Y-%m-%d')} ~ {compare_to.strftime('%Y-%m-%d')}")


def main():
    parser = argparse.ArgumentParser(description="OBS Bucket Total Request Statistics")
    parser.add_argument("--region", required=True, help="Huawei Cloud region, e.g., cn-south-1")
    parser.add_argument("--bucket", required=True, help="OBS bucket name")
    parser.add_argument("--period", choices=["this_month", "last_month", "last_30d"],
                        help="Time period: this_month (this month), last_month (last month), last_30d (last 30 days)")
    parser.add_argument("--from", dest="from_str", help="Custom start date, format: YYYY-MM-DD")
    parser.add_argument("--to", dest="to_str", help="Custom end date, format: YYYY-MM-DD")
    parser.add_argument("--include-errors", action="store_true",
                        help="Also query 4xx/5xx error request counts")
    args = parser.parse_args()

    if not args.period and not (args.from_str and args.to_str):
        parser.error("Either --period or --from/--to must be specified")

    from_dt, to_dt, compare_from, compare_to = resolve_time_range(
        args.period, args.from_str, args.to_str
    )
    from_ms = dt_to_ms(from_dt)
    to_ms = dt_to_ms(to_dt)
    compare_from_ms = dt_to_ms(compare_from)
    compare_to_ms = dt_to_ms(compare_to)

    cur = query_requests(args.region, args.bucket, from_ms, to_ms,
                         include_errors=args.include_errors)
    cmp = query_requests(args.region, args.bucket, compare_from_ms, compare_to_ms,
                         include_errors=args.include_errors)

    print()
    print_request_report(args.bucket, cur, cmp, from_dt, to_dt,
                         compare_from, compare_to,
                         include_errors=args.include_errors)


if __name__ == "__main__":
    main()
