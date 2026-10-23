#!/usr/bin/env python3
"""
Analyze event baseline binding rate at instance level using CES alarm rule data.

CES event alarm rules (type=EVENT_SYS/EVENT_CUSTOM) contain:
- service (extracted from namespace), event_ids (from policies[].metric_name),
  resources (list of dimension dicts with instance IDs)

No resource group mapping or tenant-level matching needed — resources are
embedded directly in the alarm rules. Single-customer mode only.

Input:
  - online_notification_rules.json (produced by main_event.py)
  - core_instances.json (single customer, flat instances dict)
  - event_baseline.json (baseline event records)
"""

import json
import re
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("event-bind-analysis")

DEFAULT_CORE = str(Path(INTERMEDIATE_DIR) / "core_instances.json")
DEFAULT_NOTIFICATION_RULES = str(Path(INTERMEDIATE_DIR) / "online_notification_rules.json")
DEFAULT_EVENT_BASELINE = str(Path(INTERMEDIATE_DIR) / "event_baseline.json")
DEFAULT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "event_bind_report.json")

BASELINE_TO_RULE_SVC = {
    "RDS": "RDS", "GeminiDB": "NoSQL", "ECS": "ECS", "BMS": "BMS",
    "DDS": "DDS", "GAUSSDB": "GAUSSDB", "DCS": "DCS", "TaurusDB": "GAUSSDBV5",
    "DDM": "DMS", "OBS": "OBS", "EIP": "EIP", "GEIP": "EIP", "CBR": "CBR",
    "GA": "GA", "HSS": "HSS", "ELB": "ELB", "SecMaster": "SecMaster",
    "CSMS": "CSMS", "modelarts": "ModelArts", "SFSTurbo": "EFS",
}

CORE_TO_BASELINE_SVC = {"EIP": "EIP"}

RULE_TO_CORE_SVC = defaultdict(list)
for _core_svc in list(CORE_TO_BASELINE_SVC.keys()) + [
    k for k in BASELINE_TO_RULE_SVC.keys() if k not in CORE_TO_BASELINE_SVC
]:
    _baseline_svc = CORE_TO_BASELINE_SVC.get(_core_svc, _core_svc)
    _rule_svc = BASELINE_TO_RULE_SVC.get(_baseline_svc, _baseline_svc)
    RULE_TO_CORE_SVC[_rule_svc].append(_core_svc)
RULE_TO_CORE_SVC = dict(RULE_TO_CORE_SVC)

EVENT_BASELINE_SERVICES_WITH_DIM = {"RDS", "DCS", "GeminiDB"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_id(raw_id):
    if not raw_id:
        return ""
    return raw_id.replace("-", "").lower().strip()


def extract_uuids(text):
    if not text:
        return set()
    return set(re.findall(
        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', text
    ))


def _get_dim_matching_events(metric_dim, baseline_records):
    matching = []
    for rec in baseline_records:
        dims = rec.get("维度", [])
        if not dims:
            continue
        if metric_dim in dims:
            matching.append(rec)
    return matching


def _build_svc_dim_key(core_svc, baseline_svc, metric_dim):
    if baseline_svc in EVENT_BASELINE_SERVICES_WITH_DIM and metric_dim:
        return f"{core_svc}|{metric_dim}"
    return core_svc


def _build_svc_dim_display(core_svc, baseline_svc, metric_dim):
    if baseline_svc in EVENT_BASELINE_SERVICES_WITH_DIM and metric_dim:
        return f"{core_svc} - {metric_dim}"
    return core_svc


def _build_instance_event_map(rules, core_instances):
    """
    Build a map: normalized_instance_id -> set of (service, event_id) tuples.

    For non-wildcard rules: match instance IDs from resources dimensions.
    For wildcard rules (empty resources): apply to all instances of the service.
    """
    inst_events = defaultdict(set)
    wildcard_count = 0
    direct_count = 0

    # Build a set of all known instance IDs per service for wildcard expansion
    all_inst_ids_by_svc = defaultdict(set)
    for core_svc, insts in core_instances.items():
        for inst in insts:
            nid = normalize_id(inst.get("instance_id", ""))
            if nid:
                all_inst_ids_by_svc[core_svc].add(nid)

    for rule in rules:
        svc = rule.get("service", "")
        event_ids = rule.get("event_ids", [])
        if not svc or not event_ids:
            continue

        resources = rule.get("resources", [])
        is_wildcard = not resources

        if is_wildcard:
            # Wildcard rule: apply to all instances of matching core services
            core_svcs = RULE_TO_CORE_SVC.get(svc, [svc])
            for core_svc in core_svcs:
                for nid in all_inst_ids_by_svc.get(core_svc, set()):
                    for eid in event_ids:
                        inst_events[nid].add((svc, eid))
                        wildcard_count += 1
        else:
            # Non-wildcard: match specific instance IDs from resource dimensions
            for res_dims in resources:
                for dim_name, dim_value in res_dims.items():
                    if not dim_value or dim_value == "*":
                        continue
                    nid = normalize_id(dim_value)
                    if nid:
                        for eid in event_ids:
                            inst_events[nid].add((svc, eid))
                            direct_count += 1
                    # Also try UUID matching
                    uuids = extract_uuids(dim_value)
                    for uid in uuids:
                        nuid = normalize_id(uid)
                        if nuid and nuid != nid:
                            for eid in event_ids:
                                inst_events[nuid].add((svc, eid))
                                direct_count += 1

    logger.info(f"Built instance event map: {len(inst_events)} instances with events "
                f"(direct={direct_count}, wildcard={wildcard_count})")
    return inst_events


def _analyze(core_instances, inst_events, baseline):
    """Analyze event binding for a single customer (the only mode in CES)."""
    baseline_records = baseline.get("records", [])
    baseline_by_svc = defaultdict(list)
    for rec in baseline_records:
        baseline_by_svc[rec["云服务简称"]].append(rec)

    by_instance = []
    by_service = defaultdict(lambda: {
        "total_instances": 0, "bound_instances": 0, "total_baseline": 0,
        "covered_baseline": 0, "fully_bound": 0, "partially_bound": 0,
        "unbound": 0, "no_online_rules": 0, "no_baseline": 0,
    })
    total_instances = 0
    total_bound = 0
    total_covered_events = 0
    total_baseline_events = 0
    unique_instance_ids = set()
    baseline_svc_set = set(baseline_by_svc.keys())
    svc_dim_baseline_event_count = {}

    for core_svc, insts in core_instances.items():
        baseline_svc = CORE_TO_BASELINE_SVC.get(core_svc, core_svc)
        rule_svc = BASELINE_TO_RULE_SVC.get(baseline_svc, baseline_svc)
        svc_all_baseline_records = baseline_by_svc.get(baseline_svc, [])
        svc_all_baseline_event_ids = set(r.get("事件ID", "") for r in svc_all_baseline_records)
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
            norm_inst_id = normalize_id(inst_id)
            unique_instance_ids.add(inst_id)
            total_instances += 1

            metric_dim = inst.get("metric_dimension", "")
            if baseline_svc == "GeminiDB" and "," in metric_dim:
                metric_dim = metric_dim.split(",")[0]
            is_dim_svc = baseline_svc in EVENT_BASELINE_SERVICES_WITH_DIM

            if is_dim_svc and metric_dim:
                svc_baseline_records = _get_dim_matching_events(metric_dim, svc_all_baseline_records)
                svc_baseline_event_ids = set(r.get("事件ID", "") for r in svc_baseline_records)
            else:
                svc_baseline_records = svc_all_baseline_records
                svc_baseline_event_ids = svc_all_baseline_event_ids

            svc_dim_key = _build_svc_dim_key(core_svc, baseline_svc, metric_dim if is_dim_svc else "")
            svc_dim_display = _build_svc_dim_display(core_svc, baseline_svc, metric_dim if is_dim_svc else "")

            if svc_dim_key not in svc_dim_baseline_event_count:
                svc_dim_baseline_event_count[svc_dim_key] = len(svc_baseline_records)

            if inst.get("instance_non_exist"):
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "svc_dim": svc_dim_display,
                    "raw_service": raw_svc, "region": region,
                    "bound_status": "instance_non_exist",
                    "baseline_events_total": "N/A", "baseline_events_covered": "N/A",
                    "baseline_events_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "covered_events": [], "missing_events": [],
                })
                continue

            inst_event_tuples = inst_events.get(norm_inst_id, set())
            inst_svc_events = {ev_name for s, ev_name in inst_event_tuples if s == rule_svc}

            if not svc_has_baseline:
                by_service[svc_dim_key]["total_instances"] += 1
                by_service[svc_dim_key]["no_baseline"] += 1
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "svc_dim": svc_dim_display,
                    "raw_service": raw_svc, "region": region,
                    "bound_status": "no_baseline",
                    "baseline_events_total": "N/A", "baseline_events_covered": "N/A",
                    "baseline_events_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "covered_events": [], "missing_events": [],
                })
                continue

            if not inst_svc_events:
                by_service[svc_dim_key]["total_instances"] += 1
                by_service[svc_dim_key]["no_online_rules"] += 1
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "svc_dim": svc_dim_display,
                    "raw_service": raw_svc, "region": region,
                    "bound_status": "no_online_rules",
                    "baseline_events_total": len(svc_baseline_records),
                    "baseline_events_covered": 0,
                    "baseline_events_missing": len(svc_baseline_records),
                    "bind_rate": "0.0%", "bind_rate_value": 0,
                    "covered_events": [],
                    "missing_events": [
                        {"云服务简称": baseline_svc, "事件ID": r.get("事件ID", ""),
                         "事件名称": r.get("事件名称", ""), "事件说明": r.get("事件说明", ""),
                         "处理建议": r.get("处理建议", ""), "事件影响": r.get("事件影响", "")}
                        for r in svc_baseline_records
                    ],
                })
                by_service[svc_dim_key]["total_baseline"] += len(svc_baseline_records)
                total_baseline_events += len(svc_baseline_records)
                continue

            covered_event_ids = inst_svc_events & svc_baseline_event_ids
            missing_event_ids = svc_baseline_event_ids - inst_svc_events

            covered_events = []
            missing_events = []
            for r in svc_baseline_records:
                eid = r.get("事件ID", "")
                detail = {
                    "云服务简称": baseline_svc, "事件ID": eid,
                    "事件名称": r.get("事件名称", ""), "事件说明": r.get("事件说明", ""),
                    "处理建议": r.get("处理建议", ""), "事件影响": r.get("事件影响", ""),
                }
                if eid in covered_event_ids:
                    covered_events.append(detail)
                else:
                    missing_events.append(detail)

            total_baseline = len(svc_baseline_records)
            total_covered = len(covered_event_ids)
            bind_rate_val = total_covered / total_baseline if total_baseline > 0 else 0
            bind_rate = f"{bind_rate_val * 100:.1f}%" if total_baseline > 0 else "N/A"

            if total_covered >= total_baseline:
                bound_status = "fully_bound"
            elif total_covered > 0:
                bound_status = "partially_bound"
            else:
                bound_status = "unbound"

            if total_covered > 0:
                total_bound += 1
            total_covered_events += total_covered
            total_baseline_events += total_baseline

            by_service[svc_dim_key]["total_instances"] += 1
            by_service[svc_dim_key][bound_status] += 1
            if total_covered > 0:
                by_service[svc_dim_key]["bound_instances"] += 1
            by_service[svc_dim_key]["total_baseline"] += total_baseline
            by_service[svc_dim_key]["covered_baseline"] += total_covered

            by_instance.append({
                "instance_id": inst_id, "service": core_svc, "svc_dim": svc_dim_display,
                "raw_service": raw_svc, "region": region, "bound_status": bound_status,
                "baseline_events_total": total_baseline, "baseline_events_covered": total_covered,
                "baseline_events_missing": total_baseline - total_covered,
                "bind_rate": bind_rate, "bind_rate_value": round(bind_rate_val, 4),
                "covered_events": covered_events, "missing_events": missing_events,
            })

    by_service_final = {}
    for svc_dim_key, agg in by_service.items():
        if agg["total_baseline"] > 0:
            svc_rate = f"{agg['covered_baseline'] / agg['total_baseline'] * 100:.1f}%"
        else:
            svc_rate = "N/A"
        by_service_final[svc_dim_key] = {
            "total_instances": agg["total_instances"],
            "fully_bound": agg["fully_bound"],
            "partially_bound": agg["partially_bound"],
            "unbound": agg["unbound"],
            "no_online_rules": agg["no_online_rules"],
            "no_baseline": agg["no_baseline"],
            "missing_events_total": agg["total_baseline"] - agg["covered_baseline"] if agg["total_baseline"] > 0 else 0,
            "baseline_event_count": svc_dim_baseline_event_count.get(svc_dim_key, 0),
            "covered_baseline": agg["covered_baseline"],
            "total_baseline": agg["total_baseline"],
            "bind_rate": svc_rate,
        }

    if total_baseline_events > 0:
        overall_rate = f"{total_covered_events / total_baseline_events * 100:.1f}%"
    else:
        overall_rate = "N/A"

    report = {
        "summary": {
            "total_instances": len(unique_instance_ids),
            "bound_instances": total_bound,
            "overall_rate": overall_rate,
            "total_covered_events": total_covered_events,
            "total_baseline_events": total_baseline_events,
            "missing_events_total": total_baseline_events - total_covered_events,
            "no_rules_instances": sum(1 for r in by_instance if r.get("bound_status") == "no_online_rules"),
            "no_baseline_instances": sum(1 for r in by_instance if r.get("bound_status") == "no_baseline"),
        },
        "by_service": by_service_final,
        "by_instance": by_instance,
    }
    return report


def analyze(core_path, notification_rules_path, event_baseline_path, output_path):
    core = load_json(core_path)
    rules_data = load_json(notification_rules_path)
    baseline = load_json(event_baseline_path)

    rules = rules_data.get("rules", [])
    core_instances = core.get("instances", {})
    logger.info(f"Loaded {len(rules)} event alarm rules, {len(core_instances)} core services")

    inst_events = _build_instance_event_map(rules, core_instances)
    logger.info(f"Built instance event map: {len(inst_events)} instances with events")

    report = _analyze(core_instances, inst_events, baseline)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Report saved to {output_path}")

    summary = report["summary"]
    logger.info(f"Total: {summary['total_instances']} instances, bind_rate={summary['overall_rate']}")
    for svc_dim, info in sorted(report["by_service"].items()):
        logger.info(f"  {svc_dim}: {info['total_instances']} instances, bind_rate={info['bind_rate']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze event baseline binding rate (CES)")
    parser.add_argument("--core", default=DEFAULT_CORE)
    parser.add_argument("--notification-rules", default=DEFAULT_NOTIFICATION_RULES)
    parser.add_argument("--event-baseline", default=DEFAULT_EVENT_BASELINE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    analyze(args.core, args.notification_rules, args.event_baseline, args.output)
