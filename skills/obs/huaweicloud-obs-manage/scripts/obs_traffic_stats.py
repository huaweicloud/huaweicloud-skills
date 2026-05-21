#!/usr/bin/env python3
"""
OBS桶下载流量统计脚本

通过华为云CES（云监控服务）查询OBS桶的外网/内网下载流量，并计算月环比。

用法:
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period last_month
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month
    python3 obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20

关键经验:
    1. 必须使用流量指标(download_traffic_extranet/download_traffic_intranet)，不能用带宽指标(download_bytes)
    2. hcloud CES维度参数格式: --dim.0=bucket_name,<BucketName>，不是SDK的dimensions格式
    3. 时间范围: "本月"=自然月(当月1日~当前)，"最近一个月"=滚动30天窗口(当前-30天~当前)
    4. CES返回的sum值直接累加即为总字节数，无需乘以聚合周期
    5. hcloud所有参数必须使用 --param=value 格式（等号连接）
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
        return "N/A" if current == 0 else "新增（上期为0）"
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
        raise ValueError(f"不支持的period: {period}，可选: this_month, last_month, last_30d")

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
        print(f"警告: 查询 {metric_name} 失败: {result.stderr.strip()}", file=sys.stderr)
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
                         compare_from: datetime, compare_to: datetime, direction: str = "下载"):
    label_map = {"extranet": "外网", "intranet": "内网", "total": "总计"}
    print(f"OBS{direction}流量统计 - 桶: {bucket}")
    print("═" * 60)
    print(f"{'指标':<12s}{'当前周期':<20s}{'对照周期':<20s}{'月环比'}")
    print("─" * 60)
    for key in ["extranet", "intranet", "total"]:
        label = f"{label_map[key]}{direction}流量"
        cur_val = cur[key]
        cmp_val = cmp[key]
        print(f"{label:<12s}{fmt_bytes(cur_val):<20s}{fmt_bytes(cmp_val):<20s}{calc_pct(cur_val, cmp_val)}")
    print("═" * 60)
    print(f"当前周期: {from_dt.strftime('%Y-%m-%d')} ~ {to_dt.strftime('%Y-%m-%d')}")
    print(f"对照周期: {compare_from.strftime('%Y-%m-%d')} ~ {compare_to.strftime('%Y-%m-%d')}")


def main():
    parser = argparse.ArgumentParser(description="OBS桶下载流量统计")
    parser.add_argument("--region", required=True, help="华为云区域，如 cn-south-1")
    parser.add_argument("--bucket", required=True, help="OBS桶名")
    parser.add_argument("--period", choices=["this_month", "last_month", "last_30d"],
                        help="时间周期: this_month(本月), last_month(上月), last_30d(最近30天)")
    parser.add_argument("--from", dest="from_str", help="自定义起始日期，格式: YYYY-MM-DD")
    parser.add_argument("--to", dest="to_str", help="自定义截止日期，格式: YYYY-MM-DD")
    parser.add_argument("--direction", choices=["download", "upload", "both"], default="download",
                        help="流量方向: download(下载), upload(上传), both(下载+上传)")
    args = parser.parse_args()

    if not args.period and not (args.from_str and args.to_str):
        parser.error("必须指定 --period 或 --from/--to")

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
        label = "下载" if d == "download" else "上传"
        cur = query_traffic(args.region, args.bucket, from_ms, to_ms, direction=d)
        cmp = query_traffic(args.region, args.bucket, compare_from_ms, compare_to_ms, direction=d)
        print()
        print_traffic_report(args.bucket, cur, cmp, from_dt, to_dt, compare_from, compare_to, direction=label)


if __name__ == "__main__":
    main()
