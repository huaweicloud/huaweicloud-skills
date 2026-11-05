#!/usr/bin/env python3
"""huawei-cloud-eip-query - Huawei Cloud EIP query and bandwidth monitoring.

Query Elastic Public IP (EIP) resources and their Cloud Eye (CES) bandwidth
monitoring data: bandwidth usage rate, inbound/outbound traffic, peak/avg
bandwidth, over a configurable time range.

Quality reporting: skill-quality-cli (see SKILL.md quality-reporting section).
"""
import argparse
import json
import os
import subprocess
import sys

HCLOUD = os.environ.get("HCLOUD_BIN", "hcloud")
REGION = os.environ.get("HUAWEICLOUD_SDK_REGION", "cn-north-4")

METRIC_NAMESPACE = "SYS.VPC"

EIP_METRICS = {
    "upstream_bandwidth": "出网带宽 (bit/s)",
    "downstream_bandwidth": "入网带宽 (bit/s)",
    "upstream_bandwidth_usage": "出网带宽使用率 (%)",
    "downstream_bandwidth_usage": "入网带宽使用率 (%)",
    "up_stream": "流出流量 (Byte)",
    "down_stream": "流入流量 (Byte)",
}

FILTERS = ["average", "variance", "min", "max", "sum"]
PERIODS = [1, 60, 300, 1200, 3600, 14400, 86400]


class HCloudError(RuntimeError):
    """Raised when the hcloud CLI returns an error response."""


def _extract_json(stdout):
    """Extract a JSON object from hcloud output that may include diagnostic text."""
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(stdout[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None


def _raise_hcloud_error(args, hint):
    raise HCloudError(
        f"hcloud {' '.join(args)} failed: {hint}".strip()
    )


def _check_hcloud_error(data, args):
    if not isinstance(data, dict):
        return data
    http_code = data.get("http_code")
    if isinstance(http_code, int) and http_code != 200:
        err = data.get("error") or {}
        code = err.get("code") if isinstance(err, dict) else None
        details = err.get("message") if isinstance(err, dict) else None
        _raise_hcloud_error(args, f"http {http_code}"
                            + (f" [{code}]" if code else "")
                            + (f": {details}" if details else ""))
    error_code = data.get("error_code") or data.get("code")
    if isinstance(error_code, str) and error_code:
        _raise_hcloud_error(
            args,
            f"[{error_code}] {data.get('error_msg', '') or data.get('message', '') or 'Unknown hcloud error'}",
        )
    return data


def run_hcloud(args, region=None):
    cmd = [HCLOUD] + args + [f"--cli-region={region or REGION}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        _raise_hcloud_error(
            args, proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        )
    data = _extract_json(proc.stdout)
    if data is None:
        _raise_hcloud_error(args, f"unexpected non-JSON output: {proc.stdout.strip()[:200]}")
    return _check_hcloud_error(data, args)


def list_eips(limit=None, region=None):
    params = [f"--limit={limit}"] if limit else []
    return run_hcloud(["eip", "ListPublicips/v2"] + params, region=region)


def show_eip(publicip_id, region=None):
    return run_hcloud(
        ["eip", "ShowPublicip/v2", f"--publicip_id={publicip_id}"], region=region
    )


def list_metrics(region=None):
    return run_hcloud(
        ["ces", "ListMetrics", f"--namespace={METRIC_NAMESPACE}"], region=region
    )


def show_metric(metric_name, dimension, from_ms, to_ms, period, filter_name, region=None):
    dim_str = ",".join(dimension)
    return run_hcloud(
        [
            "ces",
            "ShowMetricData",
            f"--namespace={METRIC_NAMESPACE}",
            f"--metric_name={metric_name}",
            f"--dim.0={dim_str}",
            f"--from={from_ms}",
            f"--to={to_ms}",
            f"--period={period}",
            f"--filter={filter_name}",
        ],
        region=region,
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="huawei-cloud-eip-query",
        description="Query EIP resources and their CES bandwidth monitoring data",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--region", default=None, help=f"Region (default {REGION})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", parents=[common], help="List EIPs")
    p_list.add_argument("--limit", type=int, default=None, help="Max records")
    p_list.add_argument("--json", action="store_true", dest="json_out", help="Raw JSON output")

    p_show = sub.add_parser("show", parents=[common], help="Show one EIP detail")
    p_show.add_argument("--publicip_id", required=True, help="EIP resource id")

    p_metric = sub.add_parser("metric", parents=[common], help="Query EIP bandwidth monitoring data via CES")
    p_metric.add_argument("--publicip_id", help="EIP public IP id (dimension publicip_id)")
    p_metric.add_argument("--bandwidth_id", help="Bandwidth id (dimension bandwidth_id)")
    p_metric.add_argument(
        "--metric", "-m", action="append",
        help="Metric name, repeatable. Default: all EIP metrics.",
    )
    p_metric.add_argument("--filter", default="average", choices=FILTERS,
                          help="Aggregation method. max=peak, average=mean (default average)")
    p_metric.add_argument("--period", type=int, default=300, choices=PERIODS,
                          help="Aggregation period in seconds (default 300)")
    p_metric.add_argument("--from", dest="from_ms", help="Start time, Unix ms. "
                          "Default: now - 1 hour")
    p_metric.add_argument("--to", dest="to_ms", help="End time, Unix ms. Default: now")
    p_metric.add_argument("--json", action="store_true", dest="json_out",
                          help="Raw JSON output")

    return parser


def parse_time(timestr):
    if timestr is None:
        return None
    timestr = timestr.strip()
    if timestr.isdigit():
        return int(timestr)
    raise ValueError(f"invalid timestamp: {timestr} (use Unix milliseconds)")


def main():
    args = build_parser().parse_args()
    try:
        return _dispatch(args)
    except HCloudError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _dispatch(args):
    if args.command == "list":
        data = list_eips(limit=args.limit, region=args.region)
        if args.json_out:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        eips = data.get("publicips", [])
        print(f"{'id':<38} {'ip':<16} {'status':<8} {'bandwidth':<10} {'type'}")
        for e in eips:
            bw = e.get("bandwidth") or {}
            print(f"{e.get('id',''):<38} {e.get('public_ip_address',''):<16} "
                  f"{e.get('status',''):<8} {bw.get('size','') or (str(bw.get('id')) if bw.get('id') else ''):<10} "
                  f"{e.get('type','')}")
        print(f"\nTotal: {len(eips)} EIPs")
        return 0

    if args.command == "show":
        data = show_eip(args.publicip_id, region=args.region)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if args.command == "metric":
        if not args.publicip_id and not args.bandwidth_id:
            raise SystemExit("error: metric query requires --publicip_id or --bandwidth_id")
        dim = ("publicip_id", args.publicip_id) if args.publicip_id else ("bandwidth_id", args.bandwidth_id)
        from_ms = parse_time(args.from_ms)
        to_ms = parse_time(args.to_ms)
        if from_ms is None:
            from_ms = int(__import__("time").time() * 1000) - 3600_000
        if to_ms is None:
            to_ms = int(__import__("time").time() * 1000)

        metrics = args.metric or list(EIP_METRICS.keys())
        results = {}
        for m in metrics:
            if m not in EIP_METRICS:
                raise SystemExit(f"error: unknown metric '{m}'. Available: {', '.join(EIP_METRICS)}")
            results[m] = show_metric(m, dim, from_ms, to_ms, args.period, args.filter, region=args.region)

        if args.json_out:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0

        print(f"EIP {dim[1]} metrics (from={from_ms} to={to_ms} period={args.period}s filter={args.filter})")
        print("=" * 70)
        for m, data in results.items():
            pts = data.get("datapoints", []) or []
            values = [p.get(args.filter) for p in pts if args.filter in p]
            peak = max(values) if values else None
            avg = sum(values) / len(values) if values else None
            unit = pts[0].get("unit", "") if pts else ""
            print(f"{m:<28} {EIP_METRICS[m]:<16} points={len(pts):<4} "
                  f"peak={peak if peak is not None else '-':<12} avg={avg if avg is not None else '-'} {unit}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())