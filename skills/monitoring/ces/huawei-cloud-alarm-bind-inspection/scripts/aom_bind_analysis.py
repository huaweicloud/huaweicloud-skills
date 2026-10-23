#!/usr/bin/env python3
"""
AOM indicator baseline bind analysis.

Compares AOM indicator baseline (aom_indicator_baseline.json) against
AOM metric alarm rules (aom_alarm_rules.json) and core instances
(core_instances.json).

Matching logic:
- Group baseline by (云服务简称, 指标维度)
- For each group, check if core instances exist for that service
- If yes, check which baseline metrics are covered by alarm rules
- AOM alarm rules matched by alarm_rule_name or promql containing metric ID

Output: <INTERMEDIATE_DIR>/aom_indicator_bind_report.json
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aom-bind-analysis")

BASELINE_PATH = str(Path(INTERMEDIATE_DIR) / "aom_indicator_baseline.json")
ALARM_RULES_PATH = str(Path(INTERMEDIATE_DIR) / "aom_alarm_rules.json")
CORE_INSTANCES_PATH = str(Path(INTERMEDIATE_DIR) / "core_instances.json")
OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "aom_indicator_bind_report.json")


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
        logger.error("AOM indicator baseline not found, run generate_alarm_baseline.py first")
        return

    baseline_records = baseline_data.get("records", [])
    alarm_rules = (alarm_data or {}).get("rules", [])
    core_instances = (core_data or {}).get("instances", {})

    logger.info(f"Loaded: {len(baseline_records)} baseline records, "
                f"{len(alarm_rules)} alarm rules, "
                f"{sum(len(v) for v in core_instances.values())} core instances")

    # Group baseline by (云服务简称, 指标维度)
    baseline_by_svc_dim = defaultdict(list)
    for r in baseline_records:
        svc = r.get("云服务简称", "")
        dim = r.get("指标维度", "")
        baseline_by_svc_dim[(svc, dim)].append(r)

    # Group alarm rules by service (extracted from namespace or rule config)
    rules_by_svc = defaultdict(list)
    for rule in alarm_rules:
        # AOM alarm rules may have namespace or alarm_rule_name
        ns = rule.get("namespace", "")
        svc = ns.split(".")[-1] if ns and "." in ns else ns
        if not svc:
            # Try to infer from rule name or other fields
            svc = rule.get("service", "")
        rules_by_svc[svc].append(rule)

    # Build report
    report_items = []
    total_baseline = 0
    total_covered = 0
    total_no_instances = 0
    total_no_rules = 0

    for (svc, dim), records in sorted(baseline_by_svc_dim.items()):
        metric_ids = set(r.get("指标ID", "").strip() for r in records if r.get("指标ID"))
        metric_names = {r.get("指标ID", "").strip(): r.get("指标名称", "") for r in records}
        total_baseline += len(metric_ids)

        # Check if core instances exist for this service
        insts = core_instances.get(svc, [])
        if not insts:
            # No core instances for this AOM service
            total_no_instances += len(metric_ids)
            report_items.append({
                "云服务简称": svc,
                "指标维度": dim,
                "指标维度-中文": records[0].get("指标维度-中文", dim),
                "baseline_count": len(metric_ids),
                "covered_count": 0,
                "covered_metrics": [],
                "uncovered_metrics": sorted(metric_ids),
                "metric_names": metric_names,
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
            rule_name = rule.get("alarm_rule_name", "")
            promql = rule.get("promql", "")
            rule_text = f"{rule_name} {promql}"
            for mid in metric_ids:
                if mid and mid in rule_text:
                    covered.add(mid)

        uncovered = metric_ids - covered
        total_covered += len(covered)
        if not svc_rules:
            total_no_rules += len(metric_ids)

        bind_rate = f"{len(covered) / len(metric_ids) * 100:.1f}%" if metric_ids else "N/A"
        status = "no_online_rules" if not svc_rules else "analyzed"

        report_items.append({
            "云服务简称": svc,
            "指标维度": dim,
            "指标维度-中文": records[0].get("指标维度-中文", dim),
            "baseline_count": len(metric_ids),
            "covered_count": len(covered),
            "covered_metrics": sorted(covered),
            "uncovered_metrics": sorted(uncovered),
            "metric_names": metric_names,
            "instance_count": len(insts),
            "bind_rate": bind_rate,
            "status": status,
            "source_sheet": records[0].get("source_sheet", ""),
        })

    # Summary
    summary = {
        "total_baseline_metrics": total_baseline,
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
        logger.info(f"  {item['云服务简称']}|{item['指标维度-中文']}: "
                    f"{item['baseline_count']} metrics, "
                    f"instances={item['instance_count']}, "
                    f"rate={item['bind_rate']}, status={item['status']}")


if __name__ == "__main__":
    main()
