#!/usr/bin/env python3
"""
Analyze alarm binding rate using CES alarm rule data.

CES data format:
- Alarm rules have: namespace (e.g., "SYS.ECS"), policies[] (with metric_name, dimension_name),
  resources[] (with dimensions[] containing {name, value}), enabled, alarm_notifications, etc.
- No separate template/metricDTOs — metrics are directly in policies[].metric_name
- Rules are fetched per-region, so no explicit region string field

Single-customer mode only (CES uses current account's AK/SK).
"""

import json
import re
import argparse
import logging
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from regions import regions as REGIONS_LIST
from workspace import INTERMEDIATE_DIR

REGION_CN_TO_ID = {r["name"]: r["id"] for r in REGIONS_LIST}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bind-analysis")

DEFAULT_CORE = str(Path(INTERMEDIATE_DIR) / "core_instances.json")
DEFAULT_BASELINE = str(Path(INTERMEDIATE_DIR) / "indicator_baseline.json")
DEFAULT_RULES = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")
DEFAULT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "indicator_bind_report.json")

BASELINE_TO_RULE_SVC = {
    "ECS": "ECS", "RDS": "RDS", "NAT": "NAT", "DCS": "DCS", "DMS": "DMS",
    "ELB": "ELB", "WAF": "WAF", "CCE": "CCE", "GeminiDB": "GAUSSDBFORNOSQL",
    "DC": "DCAAS", "CC": "CC", "DDOS": "DDOS", "VPC": "VPC", "EVS": "EVS",
    "GEIP": "EIP", "CSS": "ES", "SFSTurbo": "EFS",
}

CORE_TO_BASELINE_SVC = {"EIP": "VPC"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_uuids(text):
    if not text:
        return set()
    return set(re.findall(
        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', text
    ))


def _extract_service_from_namespace(namespace: str) -> str:
    if not namespace:
        return ""
    parts = namespace.split(".")
    return parts[1] if len(parts) >= 2 else namespace


def _is_eip_rule(rule):
    for res in rule.get("resources", []):
        for dim in res.get("dimensions", []):
            if dim.get("name", "") == "publicip_id":
                return True
    for policy in rule.get("policies", []):
        if policy.get("dimension_name", "") == "publicip_id":
            return True
    return False


def _dim_key_matches_rule(rule_dim_key, inst_metric_dimension, baseline_svc, baseline_by_svc_dim):
    if inst_metric_dimension:
        return set(rule_dim_key.split(",")).issubset(set(inst_metric_dimension.split(",")))
    baseline_dims = set()
    for (svc, dim), _ in baseline_by_svc_dim.items():
        if svc == baseline_svc:
            baseline_dims.add(dim)
    for bdim in baseline_dims:
        if set(rule_dim_key.split(",")) == set(bdim.split(",")):
            return True
    return False


def _get_dim_key_from_resources(resources):
    if not resources:
        return ""
    for res in resources:
        dimensions = res.get("dimensions", [])
        dim_names = [d.get("name", "") for d in dimensions if d.get("name")]
        if dim_names:
            return ",".join(dim_names)
    return ""


def _get_wildcard_dim_key(rule):
    for policy in rule.get("policies", []):
        dim_name = policy.get("dimension_name", "")
        if dim_name:
            return dim_name
    return ""


def _is_wildcard_rule(rule):
    resources = rule.get("resources", [])
    if not resources:
        return True
    for res in resources:
        for dim in res.get("dimensions", []):
            if dim.get("value", "") == "*":
                return True
    return False


def _match_instance_in_resources(inst_id, resources):
    for res in resources:
        dimensions = res.get("dimensions", [])
        for dim in dimensions:
            value = dim.get("value", "")
            if not value or value == "*":
                continue
            if value == inst_id:
                dim_names = [d.get("name", "") for d in dimensions if d.get("name")]
                return ",".join(dim_names)
            uuids = extract_uuids(value)
            if uuids and inst_id in uuids:
                dim_names = [d.get("name", "") for d in dimensions if d.get("name")]
                return ",".join(dim_names)
    return None


def get_rule_service(rule):
    svc = _extract_service_from_namespace(rule.get("namespace", ""))
    if svc == "VPC" and _is_eip_rule(rule):
        svc = "EIP"
    return svc


def get_rule_metrics(rule):
    metric_names = set()
    for policy in rule.get("policies", []):
        name = policy.get("metric_name", "")
        if name:
            metric_names.add(name.lstrip("#"))
    return metric_names


def _collect_instance_online_dims(inst_id, svc_rules, inst_region="",
                                   inst_metric_dimension="", baseline_svc="",
                                   baseline_by_svc_dim=None):
    inst_dim_metrics = defaultdict(set)
    covering_rules_count = 0

    # Phase 1: Non-wildcard rules
    for rule in svc_rules:
        if _is_wildcard_rule(rule):
            continue
        matched_dim_key = _match_instance_in_resources(inst_id, rule.get("resources", []))
        if not matched_dim_key:
            continue
        if baseline_svc == "VPC" and matched_dim_key == "bandwidth_id,publicip_id":
            matched_dim_key = "publicip_id"
        covering_rules_count += 1
        for metric_name in get_rule_metrics(rule):
            inst_dim_metrics[matched_dim_key].add(metric_name)

    # Phase 2: Wildcard rules
    for rule in svc_rules:
        if not _is_wildcard_rule(rule):
            continue
        wildcard_dim_key = _get_wildcard_dim_key(rule)
        if not wildcard_dim_key:
            wildcard_dim_key = _get_dim_key_from_resources(rule.get("resources", []))
        if not wildcard_dim_key:
            continue
        if baseline_svc == "VPC" and wildcard_dim_key == "bandwidth_id,publicip_id":
            wildcard_dim_key = "publicip_id"
        rule_region = rule.get("region", "")
        if rule_region and inst_region:
            inst_region_id = REGION_CN_TO_ID.get(inst_region, inst_region)
            if rule_region != inst_region and rule_region != inst_region_id:
                continue
        if baseline_by_svc_dim is not None:
            if not _dim_key_matches_rule(wildcard_dim_key, inst_metric_dimension,
                                          baseline_svc, baseline_by_svc_dim):
                continue
        covering_rules_count += 1
        for metric_name in get_rule_metrics(rule):
            inst_dim_metrics[wildcard_dim_key].add(metric_name)

    return inst_dim_metrics, covering_rules_count


def _match_online_dim_to_baseline_dim(online_dim_key, baseline_svc, baseline_by_svc_dim):
    online_parts = set(online_dim_key.split(","))
    for (svc, dim), _ in baseline_by_svc_dim.items():
        if svc != baseline_svc:
            continue
        baseline_parts = set(dim.split(","))
        if online_parts == baseline_parts:
            yield dim


def _save_report(report, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Report saved to {output_path}")


def _analyze(core_instances, rules, baseline):
    """Analyze alarm binding for a single customer (the only mode in CES)."""
    baseline_by_svc_dim = defaultdict(list)
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        baseline_by_svc_dim[(svc, dim)].append(rec)

    svc_dim_cn_map = {}
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        dim_cn = rec.get("指标维度-中文", "")
        svc_dim_cn_map[(svc, dim)] = dim_cn

    rules_by_svc = defaultdict(list)
    for rule in rules:
        svc = get_rule_service(rule)
        rules_by_svc[svc].append(rule)

    by_instance = []
    by_service_dimension = defaultdict(lambda: {
        "total_instances": 0, "bound_instances": 0,
        "fully_bound_instances": 0, "partially_bound_instances": 0,
        "unbound_instances": 0, "bound_baseline": 0, "total_baseline": 0,
    })

    total_instance_dims = 0
    total_bound = 0
    total_bound_baseline = 0
    total_baseline_metrics = 0
    unique_instance_ids = set()
    baseline_svc_set = set(svc for svc, dim in baseline_by_svc_dim.keys())

    for core_svc, insts in core_instances.items():
        baseline_svc = CORE_TO_BASELINE_SVC.get(core_svc, core_svc)
        rule_svc = BASELINE_TO_RULE_SVC.get(baseline_svc, baseline_svc)
        if rule_svc == "VPC" and core_svc == "EIP":
            rule_svc = "EIP"
        svc_rules = rules_by_svc.get(rule_svc, [])
        svc_has_baseline = baseline_svc in baseline_svc_set

        seen_ids = set()
        deduped_insts = []
        for inst in insts:
            if inst["instance_id"] not in seen_ids:
                seen_ids.add(inst["instance_id"])
                deduped_insts.append(inst)

        for inst in deduped_insts:
            inst_id = inst["instance_id"]
            raw_svc = inst.get("raw_service", core_svc)
            region = inst.get("region", "")
            inst_metric_dimension = inst.get("metric_dimension", "")
            unique_instance_ids.add(inst_id)

            if inst.get("instance_non_exist"):
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                    "region": region, "metric_dimension": "", "metric_dimension_cn": "无该实例",
                    "baseline_metrics_total": "N/A", "baseline_metrics_bound": "N/A",
                    "baseline_metrics_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "bound_status": "instance_non_exist", "covering_rules_count": 0, "metrics_coverage": {},
                })
                continue

            if not svc_has_baseline:
                total_instance_dims += 1
                svc_dim_key = f"{core_svc}|无指标基线"
                by_service_dimension[svc_dim_key]["total_instances"] += 1
                _, covering_rules_count = _collect_instance_online_dims(
                    inst_id, svc_rules, inst_region=region,
                    inst_metric_dimension=inst_metric_dimension,
                    baseline_svc=baseline_svc, baseline_by_svc_dim=baseline_by_svc_dim,
                )
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                    "region": region, "metric_dimension": "", "metric_dimension_cn": "无指标基线",
                    "baseline_metrics_total": "N/A", "baseline_metrics_bound": "N/A",
                    "baseline_metrics_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "bound_status": "no_baseline", "covering_rules_count": covering_rules_count,
                    "metrics_coverage": {},
                })
                continue

            inst_dim_metrics, covering_rules_count = _collect_instance_online_dims(
                inst_id, svc_rules, inst_region=region,
                inst_metric_dimension=inst_metric_dimension,
                baseline_svc=baseline_svc, baseline_by_svc_dim=baseline_by_svc_dim,
            )

            if not inst_dim_metrics:
                target_dims = []
                if inst_metric_dimension:
                    for (svc, dim), recs in baseline_by_svc_dim.items():
                        if svc == baseline_svc and set(dim.split(",")).issubset(set(inst_metric_dimension.split(","))):
                            target_dims.append(dim)

                if not target_dims:
                    total_instance_dims += 1
                    svc_dim_key = f"{core_svc}|未配置"
                    by_service_dimension[svc_dim_key]["total_instances"] += 1
                    by_instance.append({
                        "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                        "region": region, "metric_dimension": "", "metric_dimension_cn": "未配置",
                        "baseline_metrics_total": "N/A", "baseline_metrics_bound": "N/A",
                        "baseline_metrics_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                        "bound_status": "no_online_rules", "covering_rules_count": 0, "metrics_coverage": {},
                    })
                    continue

                for baseline_dim in target_dims:
                    baseline_metrics = baseline_by_svc_dim.get((baseline_svc, baseline_dim), [])
                    baseline_metric_ids = set(r["指标ID"] for r in baseline_metrics)
                    dim_cn = svc_dim_cn_map.get((baseline_svc, baseline_dim), "")
                    total_instance_dims += 1
                    total_baseline_metrics += len(baseline_metric_ids)
                    bind_rate = "0.0%" if baseline_metric_ids else "N/A"
                    metrics_coverage = {mid: False for mid in sorted(baseline_metric_ids)}
                    svc_dim_key = f"{core_svc}|{baseline_dim}"
                    by_service_dimension[svc_dim_key]["total_instances"] += 1
                    by_service_dimension[svc_dim_key]["unbound_instances"] += 1
                    by_service_dimension[svc_dim_key]["total_baseline"] += len(baseline_metric_ids)
                    by_instance.append({
                        "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                        "region": region, "metric_dimension": baseline_dim, "metric_dimension_cn": dim_cn,
                        "baseline_metrics_total": len(baseline_metric_ids), "baseline_metrics_bound": 0,
                        "baseline_metrics_missing": len(baseline_metric_ids), "bind_rate": bind_rate,
                        "bind_rate_value": 0, "bound_status": "no_online_rules",
                        "covering_rules_count": 0, "metrics_coverage": metrics_coverage,
                    })
                continue

            has_matched_dim = False
            for online_dim_key, online_metric_ids in sorted(inst_dim_metrics.items()):
                matched_baseline_dims = list(_match_online_dim_to_baseline_dim(
                    online_dim_key, baseline_svc, baseline_by_svc_dim
                ))
                if not matched_baseline_dims:
                    continue
                has_matched_dim = True
                for baseline_dim in matched_baseline_dims:
                    baseline_metrics = baseline_by_svc_dim.get((baseline_svc, baseline_dim), [])
                    baseline_metric_ids = set(r["指标ID"] for r in baseline_metrics)
                    dim_cn = svc_dim_cn_map.get((baseline_svc, baseline_dim), "")
                    bound_metric_ids = online_metric_ids & baseline_metric_ids
                    missing_metric_ids = baseline_metric_ids - online_metric_ids
                    if bound_metric_ids:
                        bound_status = "partially_bound" if missing_metric_ids else "fully_bound"
                    else:
                        bound_status = "unbound"
                    total_instance_dims += 1
                    if bound_metric_ids:
                        total_bound += 1
                    total_bound_baseline += len(bound_metric_ids)
                    total_baseline_metrics += len(baseline_metric_ids)
                    bind_rate_val = len(bound_metric_ids) / len(baseline_metric_ids) if baseline_metric_ids else 0
                    bind_rate = f"{bind_rate_val * 100:.1f}%" if baseline_metric_ids else "N/A"
                    metrics_coverage = {mid: (mid in bound_metric_ids) for mid in sorted(baseline_metric_ids)}
                    svc_dim_key = f"{core_svc}|{baseline_dim}"
                    by_service_dimension[svc_dim_key]["total_instances"] += 1
                    if bound_status == "fully_bound":
                        by_service_dimension[svc_dim_key]["fully_bound_instances"] += 1
                        by_service_dimension[svc_dim_key]["bound_instances"] += 1
                    elif bound_status == "partially_bound":
                        by_service_dimension[svc_dim_key]["partially_bound_instances"] += 1
                        by_service_dimension[svc_dim_key]["bound_instances"] += 1
                    else:
                        by_service_dimension[svc_dim_key]["unbound_instances"] += 1
                    by_service_dimension[svc_dim_key]["bound_baseline"] += len(bound_metric_ids)
                    by_service_dimension[svc_dim_key]["total_baseline"] += len(baseline_metric_ids)
                    by_instance.append({
                        "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                        "region": region, "metric_dimension": baseline_dim, "metric_dimension_cn": dim_cn,
                        "baseline_metrics_total": len(baseline_metric_ids),
                        "baseline_metrics_bound": len(bound_metric_ids),
                        "baseline_metrics_missing": len(missing_metric_ids),
                        "bind_rate": bind_rate, "bind_rate_value": round(bind_rate_val, 4),
                        "bound_status": bound_status, "covering_rules_count": covering_rules_count,
                        "metrics_coverage": metrics_coverage,
                    })

            if not has_matched_dim:
                total_instance_dims += 1
                svc_dim_key = f"{core_svc}|无指标基线"
                by_service_dimension[svc_dim_key]["total_instances"] += 1
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "raw_service": raw_svc,
                    "region": region, "metric_dimension": "", "metric_dimension_cn": "无指标基线",
                    "baseline_metrics_total": "N/A", "baseline_metrics_bound": "N/A",
                    "baseline_metrics_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "bound_status": "no_baseline", "covering_rules_count": covering_rules_count,
                    "metrics_coverage": {},
                })

    by_service_dimension_final = {}
    for svc_dim_key, agg in by_service_dimension.items():
        if svc_dim_key.endswith("|未配置") or svc_dim_key.endswith("|无指标基线"):
            by_service_dimension_final[svc_dim_key] = {
                "total_instances": agg["total_instances"], "bound_instances": "-",
                "baseline_metrics_count": "-", "avg_bind_rate": "N/A",
                "bound_baseline": "-", "total_baseline": "-",
            }
        else:
            parts = svc_dim_key.split("|")
            core_svc = parts[0]
            baseline_svc = CORE_TO_BASELINE_SVC.get(core_svc, core_svc)
            baseline_dim = parts[1] if len(parts) > 1 else ""
            baseline_metrics = baseline_by_svc_dim.get((baseline_svc, baseline_dim), [])
            baseline_metric_ids = set(r["指标ID"] for r in baseline_metrics)
            if agg["total_baseline"] > 0:
                svc_bind_rate = f"{agg['bound_baseline'] / agg['total_baseline'] * 100:.1f}%"
            else:
                svc_bind_rate = "N/A"
            by_service_dimension_final[svc_dim_key] = {
                "total_instances": agg["total_instances"], "bound_instances": agg["bound_instances"],
                "fully_bound_instances": agg["fully_bound_instances"],
                "partially_bound_instances": agg["partially_bound_instances"],
                "unbound_instances": agg["unbound_instances"],
                "baseline_metrics_count": len(baseline_metric_ids), "avg_bind_rate": svc_bind_rate,
                "bound_baseline": agg["bound_baseline"], "total_baseline": agg["total_baseline"],
            }

    if total_baseline_metrics > 0:
        overall_rate = f"{total_bound_baseline / total_baseline_metrics * 100:.1f}%"
    else:
        overall_rate = "N/A"

    report = {
        "summary": {
            "total_instances": len(unique_instance_ids),
            "bound_instances": total_bound,
            "overall_rate": overall_rate,
            "total_bound_baseline": total_bound_baseline,
            "total_baseline_metrics": total_baseline_metrics,
            "no_rules_instances": sum(1 for r in by_instance if r.get("bound_status") == "no_online_rules"),
            "no_baseline_instances": sum(1 for r in by_instance if r.get("bound_status") == "no_baseline"),
        },
        "by_service_dimension": by_service_dimension_final,
        "by_instance": by_instance,
    }
    return report


def analyze(core_path, baseline_path, rules_path, output_path):
    core = load_json(core_path)
    baseline = load_json(baseline_path)
    rules_data = load_json(rules_path)

    # Single-customer mode only (CES)
    core_instances = core.get("instances", {})
    rules = rules_data.get("rules", [])
    logger.info(f"Analyzing: {len(core_instances)} services, {len(rules)} alarm rules")

    report = _analyze(core_instances, rules, baseline)
    _save_report(report, output_path)

    summary = report["summary"]
    logger.info(f"Total: {summary['total_instances']} instances, 指标覆盖率={summary['overall_rate']}")
    for svc_dim, info in sorted(report["by_service_dimension"].items()):
        logger.info(f"  {svc_dim}: {info['total_instances']} instances, "
                    f"{info.get('baseline_metrics_count', '-')} baseline metrics, 指标覆盖率={info['avg_bind_rate']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze alarm binding rate (CES)")
    parser.add_argument("--core", default=DEFAULT_CORE)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--rules", default=DEFAULT_RULES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    analyze(args.core, args.baseline, args.rules, args.output)
