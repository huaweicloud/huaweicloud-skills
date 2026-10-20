#!/usr/bin/env python3
"""CLI entry: fault drill steady-state metric inspection.

Usage:
  python inspect_cli.py inspect config.json                # full inspection
  python inspect_cli.py inspect config.json -o ./reports/  # specify output dir
  python inspect_cli.py smoke config.json                  # connectivity check
  python inspect_cli.py init-config                        # init config template
"""

import argparse
import logging
import os
import sys
import time

from config_loader import load_config, load_metrics, get_runtime, resolve_inspection_window, init_config
from hcloud_executor import check_hcloud, run_hcloud_json
from metric_collector import build_metric_lookup, collect_all_metrics
from status_collector import collect_all_status
from steady_state_judge import judge_all_instances
from topology_builder import build_topology
from report_builder import build_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("inspect")

# Default report output dir (under skill root templates/)
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def cmd_inspect(args):
    """Full inspection: status collection → steady-state judgment → metric collection → report generation."""
    start_time = time.time()

    # Problem 1: catch config errors and provide natural language guidance
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"❌ 配置文件未找到: {e}")
        print(f"   请检查文件路径，或运行 `python inspect_cli.py init-config --output my_config.json` 生成标准模板")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 配置校验失败: {e}")
        print(f"   请检查配置文件内容，参考 `references/metrics-reference.md` 获取合法的服务名和指标名")
        sys.exit(1)

    rt = get_runtime(config)

    # Resolve inspection time window (from timeline.phases + inspect_phase)
    try:
        start_w, end_w, duration = resolve_inspection_window(config)
    except ValueError as e:
        print(f"❌ 巡检时间窗口解析失败: {e}")
        sys.exit(1)

    logger.info("Inspection window: %s ~ %s (%d min)", start_w, end_w, duration)

    # 1. Instance status collection
    logger.info("=== Step 1: Instance status collection ===")
    instances_by_service = collect_all_status(config)
    total_instances = sum(len(v) for v in instances_by_service.values())
    logger.info("Total instances: %d", total_instances)

    # Problem 2: warn if no instances collected (possible config error)
    collection_warnings = []
    if total_instances == 0:
        collection_warnings.append(
            f"未采集到任何实例 (0 instances)。请检查区域 '{', '.join(config.get('regions', []))}' 是否正确、AK/SK 是否有权限"
        )

    # 2. Steady-state judgment (status)
    logger.info("=== Step 2: Steady-state judgment ===")
    judgment_result = judge_all_instances(instances_by_service, config["steady_state_rules"])
    g = judgment_result["global"]
    logger.info("Judgment: %s", g["summary"])

    # 3. Monitoring metric collection (normal instances only)
    logger.info("=== Step 3: Metric collection ===")
    metrics_data = load_metrics()
    metric_lookup = build_metric_lookup(metrics_data)
    metrics_by_service = collect_all_metrics(
        instances_by_service, config["steady_state_rules"],
        metric_lookup, start_w, end_w, rt,
    )

    # Problem 2: check for services with 0 metrics collected
    for svc, svc_metrics in metrics_by_service.items():
        if svc_metrics:
            continue
        # Only warn if this service had instances but no metrics were collected
        if instances_by_service.get(svc):
            collection_warnings.append(f"服务 {svc} 有实例但未采集到任何监控指标，请检查指标名是否正确")

    # 4. Topology construction
    logger.info("=== Step 4: Topology construction ===")
    topology = build_topology(judgment_result)

    # 5. Report generation
    logger.info("=== Step 5: Report generation ===")
    duration_s = time.time() - start_time
    rt_with_duration = {**rt, "_duration_minutes": duration}

    filepath = build_report(
        drill_name=config["drill_name"],
        judgment_result=judgment_result,
        instances_by_service=instances_by_service,
        metrics_by_service=metrics_by_service,
        topology=topology,
        duration_s=duration_s,
        start=start_w,
        end=end_w,
        output_dir=args.output,
        runtime=rt_with_duration,
    )

    logger.info("=== Inspection complete ===")
    logger.info("Duration: %.1fs", duration_s)
    logger.info("Report: %s", filepath)
    print(f"\n✅ Inspection complete! Report generated: {filepath}")
    print(f"   Duration: {duration_s:.1f}s | {g['summary']}")

    # Problem 2: output collection warnings
    if collection_warnings:
        print(f"   ⚠️ 警告: {'; '.join(collection_warnings)}，请检查配置后重跑")

    return filepath


def cmd_smoke(args):
    """Connectivity check: verify hcloud availability + region API reachability."""
    # Problem 1: catch config errors
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"❌ 配置文件未找到: {e}")
        print(f"   请检查文件路径，或运行 `python inspect_cli.py init-config --output my_config.json` 生成标准模板")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 配置校验失败: {e}")
        print(f"   请检查配置文件内容，参考 `references/metrics-reference.md` 获取合法的服务名和指标名")
        sys.exit(1)

    rt = get_runtime(config)
    hcloud_cmd = rt["hcloud_cmd"]
    timeout = rt["hcloud_timeout"]

    print("🔍 hcloud connectivity check...")
    if not check_hcloud(hcloud_cmd):
        print(f"❌ {hcloud_cmd} not installed or unavailable")
        return False

    regions = config.get("regions", [])
    print(f"✅ {hcloud_cmd} available")
    print(f"📋 Configured regions: {', '.join(regions)}")
    print(f"📋 Drill name: {config.get('drill_name', 'N/A')}")

    # Show timeline info
    timeline = config.get("timeline", {})
    if timeline:
        print(f"📋 Drill time: {timeline.get('drill_start', 'N/A')} ~ {timeline.get('drill_end', 'N/A')}")
        inspect_phase = timeline.get("inspect_phase", "N/A")
        print(f"📋 Inspection phase: {inspect_phase}")

    # Show service toggles
    for svc, svc_cfg in config.get("services", {}).items():
        enabled = svc_cfg.get("enabled", False)
        status = "✅ enabled" if enabled else "⬜ disabled"
        print(f"  {status}: {svc}")

    # Problem 3: track failed regions, only pass if all succeed
    failed_regions = []
    if regions:
        r = run_hcloud_json(
            ["ECS", "ListServersDetails"],
            region=regions[0], timeout=timeout, hcloud_cmd=hcloud_cmd,
        )
        if "_error" in r:
            print(f"⚠️ Region {regions[0]} ECS API test failed: {r['_error'][:100]}")
            failed_regions.append(regions[0])
        else:
            count = len(r.get("servers", []))
            print(f"\n✅ Region {regions[0]} ECS API reachable (instances: {count})")

    if failed_regions:
        print(f"\n❌ Connectivity check failed: 以下区域不可达 {failed_regions}")
        return False

    print("\n✅ Connectivity check passed")
    return True


def cmd_init_config(args):
    """Initialize config template."""
    init_config(args.output)
    print(f"✅ Config template generated: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="Fault drill steady-state inspection tool",
    )
    sub = parser.add_subparsers(dest="command", help="subcommand")

    p_inspect = sub.add_parser("inspect", help="Full inspection (status + metrics + report)")
    p_inspect.add_argument("config", help="Config file path")
    p_inspect.add_argument("-o", "--output", help="Report output directory", default=DEFAULT_OUTPUT_DIR)

    p_smoke = sub.add_parser("smoke", help="Connectivity check")
    p_smoke.add_argument("config", help="Config file path")

    p_init = sub.add_parser("init-config", help="Initialize config template")
    p_init.add_argument("-o", "--output", help="Output path", default="config.json")

    args = parser.parse_args()
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "smoke":
        cmd_smoke(args)
    elif args.command == "init-config":
        cmd_init_config(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
