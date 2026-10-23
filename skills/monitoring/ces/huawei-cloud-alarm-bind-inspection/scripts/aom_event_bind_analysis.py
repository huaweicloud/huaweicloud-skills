#!/usr/bin/env python3
"""
AOM event baseline bind analysis.

Compares AOM event baseline (aom_event_baseline.json) against
AOM event alarm rules (aom_event_alarm_rules.json) and core instances
(core_instances.json).

Matching logic:
- Group baseline by 云服务简称
- For each service, check if core instances exist
- If yes, check which baseline events are covered by event alarm rules
- AOM event alarm rules matched by event ID in rule config

Output: <INTERMEDIATE_DIR>/aom_event_bind_report.json
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aom-event-bind-analysis")

BASELINE_PATH = str(Path(INTERMEDIATE_DIR) / "aom_event_baseline.json")
ALARM_RULES_PATH = str(Path(INTERMEDIATE_DIR) / "aom_event_alarm_rules.json")
CORE_INSTANCES_PATH = str(Path(INTERMEDIATE_DIR) / "core_instances.json")
OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "aom_event_bind_report.json")


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return None


def main():
    # Load data
    baseline_data = _load_json(BASELINE_PATH)
    alarm_data = _load_json(ALARM_RULES_PATH)
    core_data = _load_json(CORE_INSTANCES_PATH)

    if not baseline_data:
        logger.error("AOM event baseline not found, run generate_alarm_baseline.py first")
        return

    baseline_records = baseline_data.get("records", [])
    alarm_rules = (alarm_data or {}).get("rules", [])
    core_instances = (core_data or {}).get("instances", {})

    logger.info(f"Loaded: {len(baseline_records)} baseline events, "
                f"{len(alarm_rules)} event alarm rules, "
                f"{sum(len(v) for v in core_instances.values())} core instances")

    # Group baseline by 云服务简称
    baseline_by_svc = defaultdict(list)
    for r in baseline_records:
        svc = r.get("云服务简称", "")
        baseline_by_svc[svc].append(r)

    # Group event alarm rules by service
    rules_by_svc = defaultdict(list)
    for rule in alarm_rules:
        ns = rule.get("namespace", "")
        svc = ns.split(".")[-1] if ns and "." in ns else ns
        if not svc:
            svc = rule.get("service", "")
        rules_by_svc[svc].append(rule)

    # Build report
    report_items = []
    total_baseline = 0
    total_covered = 0
    total_no_instances = 0
    total_no_rules = 0

    for svc, records in sorted(baseline_by_svc.items()):
        event_ids = set(r.get("事件ID", "").strip() for r in records if r.get("事件ID"))
        event_names = {r.get("事件ID", "").strip(): r.get("事件名称", "") for r in records}
        total_baseline += len(event_ids)

        # Check if core instances exist for this service
        insts = core_instances.get(svc, [])
        if not insts:
            total_no_instances += len(event_ids)
            report_items.append({
                "云服务简称": svc,
                "baseline_count": len(event_ids),
                "covered_count": 0,
                "covered_events": [],
                "uncovered_events": sorted(event_ids),
                "event_names": event_names,
                "instance_count": 0,
                "bind_rate": "N/A",
                "status": "no_core_instances",
                "source_sheet": records[0].get("source_sheet", ""),
            })
            continue

        # Check alarm rule coverage
        svc_rules = rules_by_svc.get(svc, [])
        covered = set()
        for rule in svc_rules:
            rule_text = json.dumps(rule, ensure_ascii=False)
            for eid in event_ids:
                if eid and eid in rule_text:
                    covered.add(eid)

        uncovered = event_ids - covered
        total_covered += len(covered)
        if not svc_rules:
            total_no_rules += len(event_ids)

        bind_rate = f"{len(covered) / len(event_ids) * 100:.1f}%" if event_ids else "N/A"
        status = "no_online_rules" if not svc_rules else "analyzed"

        report_items.append({
            "云服务简称": svc,
            "baseline_count": len(event_ids),
            "covered_count": len(covered),
            "covered_events": sorted(covered),
            "uncovered_events": sorted(uncovered),
            "event_names": event_names,
            "instance_count": len(insts),
            "bind_rate": bind_rate,
            "status": status,
            "source_sheet": records[0].get("source_sheet", ""),
        })

    # Summary
    summary = {
        "total_baseline_events": total_baseline,
        "total_covered": total_covered,
        "total_no_core_instances": total_no_instances,
        "total_no_online_rules": total_no_rules,
        "overall_coverage": f"{total_covered / total_baseline * 100:.1f}%" if total_baseline else "N/A",
    }

    output = {
        "summary": summary,
        "items": report_items,
    }

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Report saved to {OUTPUT_PATH}")
    logger.info(f"Total baseline: {total_baseline}, covered: {total_covered}, "
                f"coverage: {summary['overall_coverage']}")
    for item in report_items:
        logger.info(f"  {item['云服务简称']}: "
                    f"{item['baseline_count']} events, "
                    f"instances={item['instance_count']}, "
                    f"rate={item['bind_rate']}, status={item['status']}")


if __name__ == "__main__":
    main()
