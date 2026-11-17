#!/usr/bin/env python3
"""
Analyze event baseline binding rate at instance level using CES alarm rule data.

CES event alarm rules (type=EVENT_SYS/EVENT_CUSTOM) contain:
- service (extracted from namespace), event_ids (from policies[].metric_name),
  resources (list of dimension dicts with instance IDs)

No resource group mapping or tenant-level matching needed — resources are
embedded directly in the alarm rules. Single-customer mode only.

Input:
  - online_notification_rules.json (produced by main_alarm.py)
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

# AOM inputs (merged into the same unified report)
DEFAULT_AOM_BASELINE = str(Path(INTERMEDIATE_DIR) / "aom_event_baseline.json")
DEFAULT_AOM_RULES = str(Path(INTERMEDIATE_DIR) / "aom_notification_rules.json")

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
    # Split instance dimension into a set of component parts for subset matching
    inst_dim_parts = set(d.strip() for d in metric_dim.split(",")) if metric_dim else set()
    for rec in baseline_records:
        dims = rec.get("维度", [])
        if not dims:
            continue
        # Match if any baseline dimension is exact or a subset of instance dimension parts
        for bd in dims:
            bd_parts = set(d.strip() for d in bd.split(","))
            if bd_parts and bd_parts.issubset(inst_dim_parts):
                matching.append(rec)
                break
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

    Region-aware matching:
    - If resources is empty (wildcard): match all instances of the same
      region + service.
    - If resources is not empty: match instances from the rule's resource_ids
      array, filtered by the same region + service.
    """
    inst_events = defaultdict(set)
    wildcard_count = 0
    direct_count = 0

    # Build index: (core_svc, region) -> set of normalized instance IDs
    all_inst_ids_by_svc_region = defaultdict(set)
    for core_svc, insts in core_instances.items():
        for inst in insts:
            nid = normalize_id(inst.get("instance_id", ""))
            region = inst.get("region", "")
            if nid:
                all_inst_ids_by_svc_region[(core_svc, region)].add(nid)

    for rule in rules:
        svc = rule.get("service", "")
        event_ids = rule.get("event_ids", [])
        if not svc or not event_ids:
            continue

        rule_region = rule.get("region", "")
        resources = rule.get("resources", [])
        core_svcs = RULE_TO_CORE_SVC.get(svc, [svc])

        # Determine if this is a wildcard rule:
        # - resources is empty, OR
        # - resources is non-empty but all dimensions are empty (no dimension filter)
        is_wildcard = not resources
        if not is_wildcard:
            has_dims = False
            for res in resources:
                if res.get("dimensions"):
                    has_dims = True
                    break
            is_wildcard = not has_dims

        if is_wildcard:
            # Wildcard rule: match all instances of the same region + service
            for core_svc in core_svcs:
                for nid in all_inst_ids_by_svc_region.get((core_svc, rule_region), set()):
                    for eid in event_ids:
                        inst_events[nid].add((svc, eid))
                        wildcard_count += 1
        else:
            # Non-wildcard: match specific resource IDs from resource_ids field
            resource_ids = rule.get("resource_ids", [])
            for rid in resource_ids:
                nid = normalize_id(rid)
                if not nid:
                    continue
                # Verify this ID belongs to the same region + service
                matched = False
                for core_svc in core_svcs:
                    if nid in all_inst_ids_by_svc_region.get((core_svc, rule_region), set()):
                        for eid in event_ids:
                            inst_events[nid].add((svc, eid))
                            direct_count += 1
                        matched = True
                        break
                # If not found in same region+service, still add it (the
                # instance might exist but not in core_instances, e.g. deleted)
                if not matched:
                    for eid in event_ids:
                        inst_events[nid].add((svc, eid))
                        direct_count += 1

    logger.info(f"Built instance event map: {len(inst_events)} instances with events "
                f"(direct={direct_count}, wildcard={wildcard_count})")
    return inst_events


def _analyze(core_instances, inst_events, baseline, ecs_special_records=None):
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
            else:
                svc_baseline_records = svc_all_baseline_records
            # Deduplicate baseline records by event ID (baseline Excel may have duplicate rows)
            _seen_eids = set()
            _deduped = []
            for _r in svc_baseline_records:
                _eid = _r.get("事件ID", "")
                if _eid not in _seen_eids:
                    _seen_eids.add(_eid)
                    _deduped.append(_r)
            svc_baseline_records = _deduped
            svc_baseline_event_ids = set(r.get("事件ID", "") for r in svc_baseline_records)

            svc_dim_key = _build_svc_dim_key(core_svc, baseline_svc, metric_dim if is_dim_svc else "")
            svc_dim_display = _build_svc_dim_display(core_svc, baseline_svc, metric_dim if is_dim_svc else "")

            # Special handling for ECS: split into ECS (regular) and ECS-NPU (AI scenario)
            if core_svc == "ECS" and ecs_special_records:
                ai_event_ids = set(r.get("事件ID", "") for r in ecs_special_records if r.get("事件ID"))
                is_npu = "npu" in metric_dim
                if is_npu:
                    svc_dim_key = "ECS|ECS-NPU"
                    svc_dim_display = "ECS - ECS-NPU"
                    # Add AI special events to baseline (deduplicated)
                    for ai_r in ecs_special_records:
                        ai_eid = ai_r.get("事件ID", "")
                        if ai_eid and ai_eid not in svc_baseline_event_ids:
                            svc_baseline_records = list(svc_baseline_records) + [ai_r]
                            svc_baseline_event_ids.add(ai_eid)
                else:
                    svc_dim_key = "ECS"
                    svc_dim_display = "ECS"
                    # Filter out AI special events from baseline (if present)
                    if ai_event_ids & svc_baseline_event_ids:
                        svc_baseline_records = [r for r in svc_baseline_records if r.get("事件ID", "") not in ai_event_ids]
                        svc_baseline_event_ids = set(r.get("事件ID", "") for r in svc_baseline_records)

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
                # AOM services (CCE/CCI/IoTDA/Modelarts) use AOM monitoring system
                AOM_SERVICES = {"CCE", "CCI", "IoTDA", "Modelarts"}
                inst_monitor_system = "AOM" if core_svc in AOM_SERVICES else "CES"
                by_service[svc_dim_key]["total_instances"] += 1
                by_service[svc_dim_key]["no_baseline"] += 1
                by_service[svc_dim_key]["monitor_system"] = inst_monitor_system
                by_instance.append({
                    "instance_id": inst_id, "service": core_svc, "svc_dim": svc_dim_display,
                    "raw_service": raw_svc, "region": region,
                    "bound_status": "no_baseline",
                    "baseline_events_total": "N/A", "baseline_events_covered": "N/A",
                    "baseline_events_missing": "N/A", "bind_rate": "N/A", "bind_rate_value": 0,
                    "covered_events": [], "missing_events": [],
                    "monitor_system": inst_monitor_system,
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


def _extract_aom_rule_service(rule):
    """Extract service name from AOM rule using alarm_source/event_source."""
    spec = rule.get("event_alarm_spec", {})
    alarm_source = spec.get("alarm_source", "")
    event_source = spec.get("event_source", "")

    if alarm_source == "CCE":
        return "CCE"
    if alarm_source == "systemEvent" and event_source:
        # Normalize: ModelArts -> Modelarts to match baseline service names
        if event_source.lower() == "modelarts":
            return "Modelarts"
        return event_source
    # Fallback: namespace or service field
    ns = rule.get("namespace", "")
    if ns:
        return ns.split(".")[-1] if "." in ns else ns
    return rule.get("service", "") or alarm_source or event_source


def _extract_aom_cluster_ids(rule):
    """Extract clusterIds from AOM rule's monitor_objects.

    Returns empty set if no clusterId found (wildcard rule).
    """
    spec = rule.get("event_alarm_spec", {})
    cluster_ids = set()
    for o in spec.get("monitor_objects", []):
        cid = o.get("clusterId", "")
        if cid:
            cluster_ids.add(cid)
    return cluster_ids


def _analyze_aom_events(core_instances, aom_event_rules, aom_event_baseline):
    """Analyze AOM event baseline binding at instance level.

    Returns structures compatible with CES _analyze() output for merging.
    """
    baseline_records = aom_event_baseline.get("records", [])

    # Group baseline by 云服务简称
    baseline_by_svc = defaultdict(list)
    for r in baseline_records:
        svc = r.get("云服务简称", "")
        baseline_by_svc[svc].append(r)

    # Group event alarm rules by service (instance-level matching)
    rules_by_svc = defaultdict(list)
    for rule in aom_event_rules:
        svc = _extract_aom_rule_service(rule)
        rules_by_svc[svc].append(rule)
        _rn = rule.get("alarm_rule_name", "")[:40]
        _ci = _extract_aom_cluster_ids(rule)
        _rr = rule.get("region", "")
        logger.debug(f"AOM rule '{_rn}' -> service={svc}, clusterIds={_ci}, region={_rr}")

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

    # Build global instance index for cross-service clusterId lookup
    all_instances_by_id = {}           # instance_id -> (instance, core_svc)
    all_inst_by_svc = defaultdict(list)  # core_svc -> [instances]
    for core_svc, insts in core_instances.items():
        for inst in insts:
            iid = inst.get("instance_id", "")
            if iid:
                all_instances_by_id[iid] = (inst, core_svc)
            all_inst_by_svc[core_svc].append(inst)

    for svc, records in sorted(baseline_by_svc.items()):
        event_ids = set(r.get("事件ID", "").strip() for r in records if r.get("事件ID"))
        svc_rules = rules_by_svc.get(svc, [])

        # Determine the scope of instances to report.
        # If core_instances has this baseline service, use it directly.
        # Otherwise, only include instances actually referenced by rules'
        # clusterIds (plus wildcard rules' service instances).
        scope_insts = core_instances.get(svc, [])
        if not scope_insts and svc_rules:
            scope_inst_ids = set()
            for rule in svc_rules:
                cluster_ids = _extract_aom_cluster_ids(rule)
                if not cluster_ids:
                    # Wildcard: include all instances of the rule's service
                    spec = rule.get("event_alarm_spec", {})
                    src = spec.get("alarm_source", "")
                    if src:
                        for inst in all_inst_by_svc.get(src, []):
                            scope_inst_ids.add(inst.get("instance_id", ""))
                else:
                    # Specific: only include instances referenced by clusterIds
                    scope_inst_ids.update(cluster_ids)
            scope_insts = []
            for iid in scope_inst_ids:
                info = all_instances_by_id.get(iid)
                if info:
                    scope_insts.append(info[0])
                else:
                    # Instance not in core_instances (e.g. deleted), still report
                    scope_insts.append({"instance_id": iid, "region": ""})

        if not scope_insts:
            continue

        for inst in scope_insts:
            inst_id = inst.get("instance_id", "")
            region = inst.get("region", "")
            unique_instance_ids.add(inst_id)
            total_instances += 1

            # Instance-level matching: per-instance covered events
            covered = set()
            for rule in svc_rules:
                rule_region = rule.get("region", "")
                # Region must match (skip if both non-empty and different)
                if rule_region and region and rule_region != region:
                    continue

                cluster_ids = _extract_aom_cluster_ids(rule)
                if not cluster_ids:
                    # Wildcard: no clusterId -> match all instances of same region + service
                    pass
                elif inst_id not in cluster_ids:
                    # Specific: clusterId doesn't match this instance
                    continue

                # Check event coverage using substring match in rule JSON
                rule_text = json.dumps(rule, ensure_ascii=False)
                for eid in event_ids:
                    if eid and eid in rule_text:
                        covered.add(eid)

            covered_event_ids = covered & event_ids
            missing_event_ids = event_ids - covered
            total_baseline = len(event_ids)
            total_covered = len(covered_event_ids)
            bind_rate_val = total_covered / total_baseline if total_baseline > 0 else 0
            bind_rate = f"{bind_rate_val * 100:.1f}%" if total_baseline > 0 else "N/A"

            if not svc_rules:
                bound_status = "no_online_rules"
            elif total_covered >= total_baseline:
                bound_status = "fully_bound"
            elif total_covered > 0:
                bound_status = "partially_bound"
            else:
                bound_status = "unbound"

            if total_covered > 0:
                total_bound += 1
            total_covered_events += total_covered
            total_baseline_events += total_baseline

            covered_events = []
            missing_events = []
            for r in records:
                eid = r.get("事件ID", "")
                detail = {
                    "云服务简称": svc, "事件ID": eid,
                    "事件名称": r.get("事件名称", ""), "事件说明": r.get("事件说明", ""),
                    "处理建议": r.get("处理建议", ""), "事件影响": r.get("事件影响", ""),
                }
                if eid in covered_event_ids:
                    covered_events.append(detail)
                else:
                    missing_events.append(detail)

            by_service[svc]["total_instances"] += 1
            by_service[svc][bound_status] += 1
            if total_covered > 0:
                by_service[svc]["bound_instances"] += 1
            by_service[svc]["total_baseline"] += total_baseline
            by_service[svc]["covered_baseline"] += total_covered

            by_instance.append({
                "instance_id": inst_id, "service": svc, "svc_dim": svc,
                "raw_service": svc, "region": region, "bound_status": bound_status,
                "baseline_events_total": total_baseline, "baseline_events_covered": total_covered,
                "baseline_events_missing": total_baseline - total_covered,
                "bind_rate": bind_rate, "bind_rate_value": round(bind_rate_val, 4),
                "covered_events": covered_events, "missing_events": missing_events,
                "monitor_system": "AOM",
            })

    by_service_final = {}
    for svc, agg in by_service.items():
        svc_rate = f"{agg['covered_baseline'] / agg['total_baseline'] * 100:.1f}%" if agg["total_baseline"] > 0 else "N/A"
        by_service_final[svc] = {
            "total_instances": agg["total_instances"],
            "fully_bound": agg["fully_bound"],
            "partially_bound": agg["partially_bound"],
            "unbound": agg["unbound"],
            "no_online_rules": agg["no_online_rules"],
            "no_baseline": agg["no_baseline"],
            "missing_events_total": agg["total_baseline"] - agg["covered_baseline"] if agg["total_baseline"] > 0 else 0,
            "baseline_event_count": 0,
            "covered_baseline": agg["covered_baseline"],
            "total_baseline": agg["total_baseline"],
            "bind_rate": svc_rate,
            "monitor_system": "AOM",
        }

    overall_rate = f"{total_covered_events / total_baseline_events * 100:.1f}%" if total_baseline_events > 0 else "N/A"
    report = {
        "summary": {
            "total_instances": len(unique_instance_ids),
            "bound_instances": total_bound,
            "overall_rate": overall_rate,
            "total_covered_events": total_covered_events,
            "total_baseline_events": total_baseline_events,
            "missing_events_total": total_baseline_events - total_covered_events,
            "no_rules_instances": sum(1 for r in by_instance if r.get("bound_status") == "no_online_rules"),
            "no_baseline_instances": 0,
        },
        "by_service": by_service_final,
        "by_instance": by_instance,
    }
    return report


def _merge_event_reports(ces_report, aom_report):
    """Merge CES and AOM event reports into one unified report."""
    for inst in ces_report["by_instance"]:
        inst.setdefault("monitor_system", "CES")
    for key, v in ces_report["by_service"].items():
        v.setdefault("monitor_system", "CES")

    merged_by_instance = ces_report["by_instance"] + aom_report["by_instance"]
    merged_by_service = {}
    merged_by_service.update(ces_report["by_service"])
    merged_by_service.update(aom_report["by_service"])

    ces_s = ces_report["summary"]
    aom_s = aom_report["summary"]
    total_baseline = ces_s.get("total_baseline_events", 0) + aom_s.get("total_baseline_events", 0)
    total_covered = ces_s.get("total_covered_events", 0) + aom_s.get("total_covered_events", 0)
    overall_rate = f"{total_covered / total_baseline * 100:.1f}%" if total_baseline > 0 else "N/A"

    merged_unique_ids = set(inst["instance_id"] for inst in merged_by_instance)
    merged = {
        "summary": {
            "total_instances": len(merged_unique_ids),
            "bound_instances": ces_s.get("bound_instances", 0) + aom_s.get("bound_instances", 0),
            "overall_rate": overall_rate,
            "total_covered_events": total_covered,
            "total_baseline_events": total_baseline,
            "missing_events_total": total_baseline - total_covered,
            "no_rules_instances": sum(1 for r in merged_by_instance if r.get("bound_status") == "no_online_rules"),
            "no_baseline_instances": sum(1 for r in merged_by_instance if r.get("bound_status") == "no_baseline"),
        },
        "by_service": merged_by_service,
        "by_instance": merged_by_instance,
    }
    return merged


def analyze(core_path, notification_rules_path, event_baseline_path, output_path,
            aom_baseline_path=None, aom_rules_path=None):
    core = load_json(core_path)
    rules_data = load_json(notification_rules_path)
    baseline = load_json(event_baseline_path)

    rules = rules_data.get("rules", [])
    core_instances = core.get("instances", {})
    logger.info(f"CES: {len(rules)} event alarm rules, {len(core_instances)} core services")

    inst_events = _build_instance_event_map(rules, core_instances)

    # Load ECS special events for AI scenario handling
    ecs_special_records = []
    ecs_special_path = str(Path(event_baseline_path).parent / "ecs_special_events.json")
    try:
        ecs_special_data = load_json(ecs_special_path)
        # Deduplicate by event ID
        seen_eids = set()
        for r in ecs_special_data.get("records", []):
            eid = r.get("事件ID", "")
            if eid and eid not in seen_eids:
                seen_eids.add(eid)
                ecs_special_records.append(r)
        logger.info(f"ECS special events loaded: {len(ecs_special_records)} unique AI scenario events")
    except Exception as e:
        logger.warning(f"Failed to load ECS special events: {e}")

    ces_report = _analyze(core_instances, inst_events, baseline, ecs_special_records=ecs_special_records)

    # AOM event analysis
    aom_report = None
    if aom_baseline_path and aom_rules_path:
        try:
            aom_baseline = load_json(aom_baseline_path)
            aom_rules_data = load_json(aom_rules_path)
            aom_rules = aom_rules_data.get("rules", [])
            logger.info(f"AOM: {len(aom_baseline.get('records', []))} event baseline records, {len(aom_rules)} event alarm rules")
            aom_report = _analyze_aom_events(core_instances, aom_rules, aom_baseline)
        except FileNotFoundError as e:
            logger.warning(f"AOM event analysis skipped: {e}")

    if aom_report:
        report = _merge_event_reports(ces_report, aom_report)
    else:
        report = ces_report
        for inst in report["by_instance"]:
            inst.setdefault("monitor_system", "CES")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Report saved to {output_path}")

    summary = report["summary"]
    logger.info(f"Total: {summary['total_instances']} instances, bind_rate={summary['overall_rate']}")
    for svc_dim, info in sorted(report["by_service"].items()):
        ms = info.get("monitor_system", "CES")
        logger.info(f"  [{ms}] {svc_dim}: {info['total_instances']} instances, bind_rate={info['bind_rate']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze event baseline binding rate (CES + AOM unified)")
    parser.add_argument("--core", default=DEFAULT_CORE)
    parser.add_argument("--notification-rules", default=DEFAULT_NOTIFICATION_RULES)
    parser.add_argument("--event-baseline", default=DEFAULT_EVENT_BASELINE)
    parser.add_argument("--aom-baseline", default=DEFAULT_AOM_BASELINE)
    parser.add_argument("--aom-rules", default=DEFAULT_AOM_RULES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    analyze(args.core, args.notification_rules, args.event_baseline, args.output,
            args.aom_baseline, args.aom_rules)
