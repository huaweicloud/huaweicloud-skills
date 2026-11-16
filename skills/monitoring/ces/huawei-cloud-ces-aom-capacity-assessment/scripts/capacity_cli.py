#!/usr/bin/env python3
"""Unified CLI entry point for the Huawei Cloud capacity assessment skill.

The model (agent) only orchestrates the flow; all numeric computation happens inside this script.

Subcommands:
  read-excel      Read Excel headers/rows and validate required columns
  collect         Collect a single metric (historical window or T-24), output peak/valley
  calculate       Pure computation (input JSON, output capacity metrics)
  assess-row      End-to-end capacity assessment for one Excel row; return cells to write
  assess-all      Full assessment (foreground or --background), write everything back to Excel when done
  assess-status   Query background task progress (pass --progress file)
  write-excel     Batch-write updates into Excel (atomic replace, no backups)
  smoke           Connectivity self-check (probes CES and AOM backends), DNS hint on failure
  info            User-facing template instructions + supported metric list (grouped by 云服务/云服务维度/关键指标)

Examples:
  python3 capacity_cli.py read-excel capacity_assessment_template.xlsx
  python3 capacity_cli.py assess-row capacity_assessment_template.xlsx --row 2 --mode historical \
      --start "2026-07-01 00:00:00" --end "2026-07-14 23:59:59"
  python3 capacity_cli.py assess-all capacity_assessment_template.xlsx --mode t24 --background
  python3 capacity_cli.py assess-status --progress capacity_assessment_template.xlsx.assess.log
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from capacity import calculator, collector            # noqa: E402
from capacity.assessor import Assessor, SERVICE_CN    # noqa: E402
from capacity.config import resolve_region            # noqa: E402
from capacity.excel_io import dump_json, read_excel, write_updates  # noqa: E402
from capacity.registry import build_registry_path     # noqa: E402


def _hcloud_path(args) -> str:
    return args.hcloud or os.environ.get("HCLOUD", "hcloud")


def cmd_read_excel(args) -> int:
    doc = read_excel(args.xlsx, args.sheet)
    print(dump_json(doc))
    return 0


def cmd_collect(args) -> int:
    from capacity.registry import MetricRegistry
    reg = MetricRegistry(build_registry_path(args.metrics))
    entry = reg.lookup(args.instance_type, args.metric)
    if entry is None:
        print(json.dumps({"ok": False, "error": "metric not in registry",
                          "suggested": reg.suggested_metrics(args.instance_type)},
                         ensure_ascii=False))
        return 1
    from capacity.assessor import _build_spec, _parse_dt
    spec = _build_spec(entry, args.instance_id, args.dim_resource_id)
    if spec is None:
        print(json.dumps({"ok": False, "error": "this metric requires --dim-resource-id"}, ensure_ascii=False))
        return 1
    backend = entry.get("backend", "ces")
    try:
        if args.t24:
            r = collector.collect_t24(resolve_region(args.region), spec,
                                      period=args.period, hcloud=_hcloud_path(args),
                                      endpoint=args.endpoint, backend=backend)
        else:
            r = collector.collect_metric(resolve_region(args.region), spec,
                                         _parse_dt(args.start), _parse_dt(args.end),
                                         period=args.period, hcloud=_hcloud_path(args),
                                         endpoint=args.endpoint, backend=backend)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    print(dump_json(r))
    return 0 if r.get("ok") else 1


def cmd_calculate(args) -> int:
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    target = data["target"]
    entrances = data.get("entrances", [])
    ceiling = data.get("ceiling")
    growth = data.get("growth", 1.0)
    mode = data.get("mode", calculator.HIST)
    res = calculator.assess(mode, target, entrances, ceiling, growth)
    print(dump_json(res.as_dict()))
    return 0


def cmd_assess_row(args) -> int:
    a = Assessor(build_registry_path(args.metrics), _hcloud_path(args))
    try:
        r = a.assess_row(args.xlsx, args.row, args.mode, args.start, args.end,
                         period=args.period, endpoint=args.endpoint, sheet=args.sheet)
    except Exception as e:
        r = {"row": args.row, "ok": False, "error": str(e)}
    print(dump_json(r))
    # Expected skips (metric_mismatch, missing_required) are not errors: exit 0
    # so that assess-all loops and CI gates do not treat them as failures.
    if r.get("ok") or r.get("skipped"):
        return 0
    return 1


def cmd_assess_all(args) -> int:
    progress = args.progress or (args.xlsx + ".assess.log")
    if args.background:
        cmd = [sys.executable, os.path.abspath(__file__), "assess-all",
               args.xlsx, "--mode", args.mode, "--progress", progress]
        if args.start:
            cmd += ["--start", args.start]
        if args.end:
            cmd += ["--end", args.end]
        if args.period:
            cmd += ["--period", str(args.period)]
        if args.sheet:
            cmd += ["--sheet", args.sheet]
        if args.endpoint:
            cmd += ["--endpoint", args.endpoint]
        if args.hcloud:
            cmd += ["--hcloud", args.hcloud]
        if args.metrics:
            cmd += ["--metrics", args.metrics]
        log = progress + ".out"
        env = dict(os.environ)
        env["CAPACITY_ASSESS_CHILD"] = "1"  # child process does not clean up progress; assess-status cleans after reading done
        with open(log, "w", encoding="utf-8") as fo:
            p = subprocess.Popen(cmd, stdout=fo, stderr=subprocess.STDOUT,
                                 start_new_session=True, env=env)
        print(json.dumps({"background": True, "pid": p.pid,
                          "progress": progress, "log": log}, ensure_ascii=False))
        return 0
    # Foreground (run directly by user, or by the background child)
    child = os.environ.get("CAPACITY_ASSESS_CHILD") == "1"
    a = Assessor(build_registry_path(args.metrics), _hcloud_path(args))
    try:
        r = a.assess_all(args.xlsx, args.mode, args.start, args.end,
                         period=args.period, sheet=args.sheet, endpoint=args.endpoint,
                         progress_file=progress)
    except Exception as e:
        r = {"done": False, "error": str(e)}
    print(dump_json(r))
    # Before the child process (background task) exits, append a completion marker, then exit; assess-status cleans it up
    if r.get("done") and not child:
        _cleanup_files(progress)
    return 0 if r.get("done") else 1


def cmd_assess_status(args) -> int:
    path = args.progress
    if not os.path.exists(path):
        print(json.dumps({"done": False, "error": f"progress file not found: {path}"}, ensure_ascii=False))
        return 1
    done = None
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("done"):
                done = obj
            lines.append(obj)
    if done:
        print(dump_json(done))
        _cleanup_files(path)
    else:
        # last progress message
        last = next((o for o in reversed(lines) if "progress" in o), None)
        print(dump_json({"done": False,
                         "progress": last.get("progress", 0) if last else 0,
                         "total": last.get("total", 0) if last else 0,
                         "events": len([o for o in lines if o.get("status")])}))
    return 0


def cmd_write_excel(args) -> int:
    with open(args.updates, encoding="utf-8") as f:
        updates = json.load(f)
    r = write_updates(args.xlsx, updates, sheet=args.sheet)
    print(dump_json(r))
    return 0 if r.get("ok") else 1


def _cleanup_files(progress: str) -> list[str]:
    """Delete the assessment progress file and its .out log. Returns the deleted file list."""
    removed = []
    for f in (progress, progress + ".out"):
        try:
            if os.path.exists(f):
                os.remove(f)
                removed.append(f)
        except OSError:
            pass
    return removed


def cmd_cleanup(args) -> int:
    """Clean up junk files associated with the xlsx: .assess.log / .assess.log.out / .tmp / all .bak-*."""
    from capacity.excel_io import _prune_backups
    removed = []
    # progress and log
    removed += _cleanup_files(args.xlsx + ".assess.log")
    # .tmp residue
    for f in (args.xlsx + ".tmp",):
        try:
            if os.path.exists(f):
                os.remove(f)
                removed.append(f)
        except OSError:
            pass
    # backups: default keeps none (--keep 0), delete all
    removed += _prune_backups(args.xlsx, keep=getattr(args, "keep", 0))
    print(dump_json({"ok": True, "removed": removed}))
    return 0


def cmd_smoke(args) -> int:
    region = args.region or "cn-east-3"
    ok, msg = collector.hcloud_smoke(region, _hcloud_path(args))
    print(json.dumps({
        "ok": ok,
        "region": region,
        "message": msg,
        "dns_hint": ("check whether /etc/hosts maps ces.<region>.myhuaweicloud.com or aom.<region>.myhuaweicloud.com "
                     "to an intranet IP (100.125.x.x). If so, write the public IP of that domain into /etc/hosts, "
                     "or use --endpoint https://<public-IP> to specify the endpoint") if not ok else None,
    }, ensure_ascii=False))
    return 0 if ok else 1

def _template_explain() -> str:
    """User-facing template instructions, including the template file location."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tpl_path = os.path.join(root, "templates", "capacity_assessment_template.xlsx")
    return f"""Huawei Cloud Capacity Assessment — Usage Guide

【What is the template】
Fill one instance per row in the Excel template (sheet name: 保障重点实例_容量管理模板).
Template file location: {tpl_path}
Each row is a target instance. The tool reads the row, collects monitoring data for the target
and the entry instance, computes 峰谷值倍数 (peak/valley multiple) and 压力系数 (pressure
coefficient), predicts the business peak (e.g. festival activity) traffic ceiling, and gives
a scale-out recommendation.

Required fields for each row (only these; run `expand` to auto-fill the rest):
- region: the instance's region (e.g. 华东-上海一)
- 实例类型: cloud service abbreviation (see the "supported instance type abbreviations" below; do NOT fill
  Chinese full names like "云服务器ECS", they cannot be recognized)
- 实例ID: the instance's unique ID
- 入口实例ID: the instance used as the business-pressure reference (e.g. an entry NAT gateway)

Auto-filled by `expand` (do NOT fill these manually; the tool populates them from the metric registry):
- 关键指标: the monitoring metric to assess — one row per metric is created by expand
- 云服务维度: the dimension category of the instance (e.g. 集群/节点/实例)
- 云服务维度资源ID: a second-dimension ID beyond the instance (e.g. a database node ID)
  expand auto-discovers all available sub-dimension values from the cloud (e.g. CCE node hostIDs via AOM ListSeries,
  DMS Kafka broker IDs via CES ListMetrics) and creates one row per value.
  For DMS, the tool auto-detects the engine subtype (kafka/rabbitmq/rocketmq) via ShowInstance;
  for GeminiDB, it auto-detects cassandra/redis via GaussDBforNoSQL ListInstances.

Optional:
- 活动增长倍数: expected growth multiple of festival traffic vs. normal (default 1.0)

Optional (assessment works without them, more accurate with them):
- 资源上限: the instance's performance ceiling (e.g. bandwidth, max connections). Although the template
  labels this column "（必填）", it is actually optional in assessment: when empty, the tool takes the default
  ceiling from the built-in metric registry by 实例类型+关键指标; some metrics have a default ceiling, some do
  not (when there is no default, the 资源上限 column stays blank and the recommendation outputs
  "现有数据不支持给出建议"). If you know the ceiling, filling it in gives a more accurate recommendation.

After assessment, the tool back-fills these result columns:
- 峰谷值倍数、压力系数、预计节日上限、资源上限、单位、扩容建议
- 近一天（t-24）mode also back-fills: 近一天（t-24）峰值、近一天（t-24）谷值、近一天（t-24）峰谷值增长倍数、
  近一天（t-24）压力系数、近一天（t-24）预计节日上限、近一天（t-24）是否需要扩容
- Historical mode appends daily peak/valley columns by date (e.g. 7/1峰值)

Four assessment modes:
1. Single-instance historical: assess one row over a specified window (--start/--end)
2. Full historical: assess every complete row over a specified window (--start/--end)
3. Single-instance 近一天（t-24）: assess one row over the last 24 hours (no time needed)
4. Full 近一天（t-24）: assess every complete row over the last 24 hours (no time needed)

【A note about ECS metrics】
- The ECS monitoring metrics currently used for assessment are collected at the physical machine
  (host) level, less accurate than data collected inside the ECS instance.
- For more accurate ECS metrics, install the Cloud Eye Agent on that ECS.
"""


def _instance_type_abbr(reg) -> str:
    """Generate the instance-type abbreviation explanation (user-facing).

    These abbreviations must exactly match the metric registry (lookup lowercases before comparing);
    the registry key for EFS Turbo is "efsturbo" — "EFS-Turbo"/"EFS Turbo" will not be recognized,
    you must fill in efsturbo.
    """
    fill_abbr = {
        "nat": "NAT", "rds": "RDS", "ecs": "ECS", "elb": "ELB", "eip": "EIP",
        "css": "CSS", "dds": "DDS", "dws": "DWS", "dcs": "DCS", "dms": "DMS",
        "taurusdb": "TaurusDB", "geminidb": "GeminiDB", "dc": "DC", "er": "ER",
        "evs": "EVS", "efsturbo": "efsturbo", "apig": "APIG", "drs": "DRS",
        "vpcep": "VPCEP", "bandwidth": "Bandwidth",
        "cce": "CCE",
    }
    supported = sorted(k for k in reg.data if isinstance(reg.data[k], dict) and not k.startswith("_"))
    abbrs = [fill_abbr.get(k, k.upper()) for k in supported]
    return (
        'Supported instance type abbreviations (fill the following abbreviations in the Excel '
        '"实例类型" column; case-insensitive. Do NOT fill Chinese full names like "云服务器ECS", '
        'such rows will be skipped):\n'
        + '、'.join(abbrs)
        + '\n(Note: for the EFS Turbo service fill in efsturbo)'
    )


def _metrics_overview(reg) -> str:
    """Output the supported metric list grouped by 云服务 -> 云服务维度 -> 关键指标 (user-facing, no internal details)."""
    lines = []
    total = 0
    svc_keys = sorted(reg.data.keys())
    for skey in svc_keys:
        entries = reg.data[skey]
        if not isinstance(entries, dict) or skey.startswith("_"):
            continue
        cn_name = SERVICE_CN.get(skey, skey)
        lines.append(f"Service: {cn_name}")
        # group by dimension
        by_dim: dict[str, list[str]] = {}
        for name, e in entries.items():
            labels = sorted({d.get("label", "") for d in e.get("dimensions", []) if d.get("label")})
            dim_key = "、".join(labels) if labels else "实例"
            by_dim.setdefault(dim_key, []).append(name)
        for dim in sorted(by_dim.keys()):
            lines.append(f"  Dimension: {dim}")
            for m in sorted(by_dim[dim], key=lambda s: s.lower()):
                lines.append(f"    - {m}")
                total += 1
        lines.append("")
    lines.append(f"Total supported metrics: {total}.")
    return "\n".join(lines)


def cmd_info(args) -> int:
    from capacity.registry import MetricRegistry
    reg = MetricRegistry(build_registry_path(getattr(args, "metrics", None)))
    print(_template_explain())
    print(_instance_type_abbr(reg))
    print()
    print("【Supported metrics】")
    print(_metrics_overview(reg))
    return 0



def cmd_expand(args) -> int:
    """Expand each instance row into one row per supported metric.

    Reads the Excel, for each row determines the service type from 实例类型,
    for DMS auto-detects the subtype (kafka/rabbitmq/rocketmq) by probing CES,
    looks up all supported metrics from the registry, fills in 关键指标/云服务维度/云服务维度资源ID
    on the original row (first metric) and inserts additional rows for the remaining metrics.
    """
    from capacity.registry import MetricRegistry
    from capacity.excel_io import expand_excel
    from capacity.assessor import _cell_map

    reg = MetricRegistry(build_registry_path(args.metrics))
    hcloud = _hcloud_path(args)

    doc = read_excel(args.xlsx, args.sheet)
    if not doc["rows"]:
        print(json.dumps({"ok": False, "error": "no data rows in Excel"}, ensure_ascii=False))
        return 1

    expansions = []
    errors = []
    # Per-service subtype caches: the same instance_id can appear under different services, and a
    # DMS/GeminiDB verdict must never be reused as a DCS instance-type verdict (or vice versa).
    dms_subtypes = {}
    geminidb_subtypes = {}
    dcs_subtypes = {}
    warnings = []
    total_metrics = 0

    for r in doc["rows"]:
        cells = _cell_map(r)
        region_raw = cells.get("region")
        itype = str(cells.get("实例类型") or "").strip().lower()
        instance_id = str(cells.get("实例ID") or "").strip()

        if not itype or not instance_id:
            errors.append({"row": r["row"], "error": "missing 实例类型 or 实例ID"})
            continue

        # Skip rows that already have 关键指标 filled (already expanded)
        existing_metric = str(cells.get("关键指标") or "").strip()
        if existing_metric:
            warnings.append({"row": r["row"], "instance_id": instance_id,
                           "warning": "关键指标 already filled, skipping (row already expanded)"})
            continue

        # Resolve region
        try:
            region = resolve_region(region_raw)
        except ValueError as e:
            errors.append({"row": r["row"], "instance_id": instance_id, "error": str(e)})
            continue

        # For DMS, detect subtype
        subtype = None
        if itype == "dms":
            if instance_id in dms_subtypes:
                subtype = dms_subtypes[instance_id]
            else:
                subtype = collector.detect_dms_subtype(
                    region, instance_id, hcloud=hcloud, endpoint=args.endpoint)
                dms_subtypes[instance_id] = subtype  # cache (including None)
            if not subtype:
                errors.append({"row": r["row"], "instance_id": instance_id,
                               "warning": "could not detect DMS subtype, expanding all DMS metrics"})

        # For GeminiDB, detect subtype (cassandra/redis)
        if itype == "geminidb":
            if instance_id in geminidb_subtypes:
                subtype = geminidb_subtypes[instance_id]
            else:
                subtype = collector.detect_geminidb_subtype(
                    region, instance_id, hcloud=hcloud, endpoint=args.endpoint)
                geminidb_subtypes[instance_id] = subtype  # cache (including None)
            if not subtype:
                errors.append({"row": r["row"], "instance_id": instance_id,
                               "warning": "could not detect GeminiDB subtype, expanding all GeminiDB metrics"})

        # For DCS, detect instance type (single/ha/cluster/proxy)
        if itype == "dcs":
            if instance_id in dcs_subtypes:
                subtype = dcs_subtypes[instance_id]
            else:
                subtype = collector.detect_dcs_instance_type(
                    region, instance_id, hcloud=hcloud, endpoint=args.endpoint)
                dcs_subtypes[instance_id] = subtype  # cache (including None)
            if not subtype:
                errors.append({"row": r["row"], "instance_id": instance_id,
                               "warning": "could not detect DCS instance type, expanding all DCS metrics"})

        # Look up all metrics for this service/subtype
        metrics_entries = reg.metrics_for_service(itype, subtype=subtype)
        if not metrics_entries:
            errors.append({"row": r["row"], "instance_id": instance_id,
                           "error": f"no metrics found for service '{itype}'"
                                    + (f" subtype '{subtype}'" if subtype else "")})
            continue

        # Build metric list for expansion
        # Cache discovered dim values by (namespace, inst_dim, inst_id, res_dim)
        # so we only query the cloud once per unique dimension combination
        dim_cache: dict[tuple, list[str]] = {}
        metric_list = []
        # Notes from the dimension discovery (instance-level filter empty / fallback used),
        # surfaced in the command's warnings so an empty discovery is never silent.
        dim_warnings: list[str] = []
        for entry in metrics_entries:
            dim_info = reg.get_dim_info(entry)
            backend = entry.get("backend", "ces")
            if dim_info["needs_dim_resource_id"]:
                if dim_info["instance_dim_name"]:
                    cache_key = (entry["namespace"],
                                 dim_info["instance_dim_name"],
                                 instance_id,
                                 dim_info["dim_resource_dim_name"])
                    if cache_key in dim_cache:
                        dim_values = dim_cache[cache_key]
                    else:
                        dim_values = collector.discover_dim_values(
                            region, entry["namespace"],
                            dim_info["instance_dim_name"], instance_id,
                            dim_info["dim_resource_dim_name"],
                            backend=backend, hcloud=hcloud, endpoint=args.endpoint,
                            warnings=dim_warnings)
                        dim_cache[cache_key] = dim_values
                else:
                    # No instance dimension (e.g. EIP/bandwidth/EVS/VPCEP):
                    # dim_resource_id IS the instance_id
                    dim_values = [instance_id]
                if dim_values:
                    # One row per discovered dimension value
                    for dv in dim_values:
                        metric_list.append({
                            "关键指标": entry["metric_name_cn"],
                            "云服务维度": dim_info["label"],
                            "云服务维度资源ID": dv,
                        })
                else:
                    # Fallback: use instance_id as dim_resource_id
                    metric_list.append({
                        "关键指标": entry["metric_name_cn"],
                        "云服务维度": dim_info["label"],
                        "云服务维度资源ID": instance_id,
                    })
            else:
                metric_list.append({
                    "关键指标": entry["metric_name_cn"],
                    "云服务维度": dim_info["label"],
                    "云服务维度资源ID": "",
                })

        for dw in dim_warnings:
            warnings.append({"row": r["row"], "instance_id": instance_id,
                             "warning": dw})

        total_metrics += len(metric_list)
        expansions.append({
            "row": r["row"],
            "instance_id": instance_id,
            "metrics": metric_list,
        })

    if not expansions:
        # All rows were skipped. If only warnings (e.g. already expanded), that is OK;
        # real errors (missing fields, no metrics) should still fail.
        only_warnings = not errors
        print(json.dumps({"ok": only_warnings, "errors": errors, "warnings": warnings,
                          "message": "no rows to expand" + (" (all already expanded)" if only_warnings else "")},
                         ensure_ascii=False))
        return 0 if only_warnings else 1

    result = expand_excel(args.xlsx, expansions, sheet=args.sheet)
    output = {
        "ok": result.get("ok", False),
        "expanded_rows": result.get("expanded_rows", 0),
        "inserted_rows": result.get("inserted_rows", 0),
        "total_metrics": total_metrics,
        "subtypes_detected": {**dms_subtypes, **geminidb_subtypes, **dcs_subtypes},
        "errors": errors + result.get("errors", []),
        "warnings": warnings,
    }
    print(dump_json(output))
    return 0 if output["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Huawei Cloud capacity assessment skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hcloud", default=None, help="path to the hcloud (KooCLI) executable")
    common.add_argument("--metrics", default=None, help="path to metrics.json")
    common.add_argument("--endpoint", default=None, help="override hcloud --cli-endpoint (CES endpoint)")

    p = sub.add_parser("read-excel", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--sheet", default=None)
    p.set_defaults(func=cmd_read_excel)

    p = sub.add_parser("collect", parents=[common])
    p.add_argument("--region", required=True)
    p.add_argument("--instance-type", required=True)
    p.add_argument("--metric", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--dim-resource-id", default=None)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--t24", action="store_true")
    p.add_argument("--period", type=int, default=300)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("calculate", parents=[common])
    p.add_argument("--input", required=True)
    p.set_defaults(func=cmd_calculate)

    p = sub.add_parser("assess-row", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--row", type=int, required=True)
    p.add_argument("--mode", choices=[calculator.HIST, calculator.T24], required=True)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--period", type=int, default=300)
    p.add_argument("--sheet", default=None)
    p.set_defaults(func=cmd_assess_row)

    p = sub.add_parser("assess-all", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--mode", choices=[calculator.HIST, calculator.T24], required=True)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--period", type=int, default=300)
    p.add_argument("--sheet", default=None)
    p.add_argument("--progress", default=None)
    p.add_argument("--background", action="store_true")
    p.set_defaults(func=cmd_assess_all)

    p = sub.add_parser("assess-status", parents=[common])
    p.add_argument("--progress", required=True)
    p.set_defaults(func=cmd_assess_status)

    p = sub.add_parser("write-excel", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--updates", required=True)
    p.add_argument("--sheet", default=None)
    p.set_defaults(func=cmd_write_excel)

    p = sub.add_parser("cleanup", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--keep", type=int, default=0)
    p.set_defaults(func=cmd_cleanup)

    p = sub.add_parser("smoke", parents=[common])
    p.add_argument("--region", default="cn-east-3")
    p.set_defaults(func=cmd_smoke)

    p = sub.add_parser("expand", parents=[common])
    p.add_argument("xlsx")
    p.add_argument("--sheet", default=None)
    p.set_defaults(func=cmd_expand)

    sub.add_parser("info", parents=[common]).set_defaults(func=cmd_info)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())