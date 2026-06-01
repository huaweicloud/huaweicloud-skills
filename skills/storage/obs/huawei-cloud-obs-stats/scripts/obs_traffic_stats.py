#!/usr/bin/env python3
"""
OBS Bucket Download Traffic Statistics Script

Queries OBS bucket extranet/intranet download traffic via Huawei Cloud CES (Cloud Eye Service)
and calculates the month-over-month change.

Usage:
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period last_month
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20

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


def sum_traffic(resp: dict) -> int:
    total = 0
    for dp in resp.get("datapoints", []):
        total += dp.get("sum", 0)
    return total


def query_traffic(region: str, bucket: str, from_ms: int, to_ms: int, direction: str = "download") -> dict:
    metrics = TRAFFIC_METRICS if direction == "download" else UPLOAD_TRAFFIC_METRICS
    result = {}
    for key, metric_name in metrics.items():
        resp = query_ces_metric(region, metric_name, bucket, from_ms, to_ms)
        result[key] = sum_traffic(resp)
    result["total"] = result["extranet"] + result["intranet"]
    return result


def print_traffic_report(bucket: str, cur: dict, cmp: dict, from_dt: datetime, to_dt: datetime,
                         compare_from: datetime, compare_to: datetime, direction: str = "Download"):
    label_map = {"extranet": "Extranet ", "intranet": "Intranet ", "total": "Total    "}
    print(f"OBS {direction} Traffic Report — Bucket: {bucket}")
    print("═" * 60)
    print(f"{'Metric':<12s}{'Current Period':<20s}{'Comparison Period':<20s}{'MoM Change'}")
    print("─" * 60)
    for key in ["extranet", "intranet", "total"]:
        label = f"{label_map[key]}{direction}"
        cur_val = cur[key]
        cmp_val = cmp[key]
        print(f"{label:<12s}{fmt_bytes(cur_val):<20s}{fmt_bytes(cmp_val):<20s}{calc_pct(cur_val, cmp_val)}")
    print("═" * 60)
    print(f"Current Period: {from_dt.strftime('%Y-%m-%d')} ~ {to_dt.strftime('%Y-%m-%d')}")
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

    directions = []
    if args.direction in ("download", "both"):
        directions.append("download")
    if args.direction in ("upload", "both"):
        directions.append("upload")

    for d in directions:
        label = "Download" if d == "download" else "Upload"
        cur = query_traffic(args.region, args.bucket, from_ms, to_ms, direction=d)
        cmp = query_traffic(args.region, args.bucket, compare_from_ms, compare_to_ms, direction=d)
        print()
        print_traffic_report(args.bucket, cur, cmp, from_dt, to_dt, compare_from, compare_to, direction=label)


if __name__ == "__main__":
    main()
