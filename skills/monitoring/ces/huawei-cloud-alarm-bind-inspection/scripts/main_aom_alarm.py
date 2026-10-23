#!/usr/bin/env python3
"""
Fetch AOM (Application Operations Management) alarm rules via hcloud CLI.
AOM alarm rules are separate from CES alarm rules.

Fetches both metric-type and event-type rules via:
  hcloud AOM ListMetricOrEventAlarmRule --alarm_rule_type=metric|event

Multi-region: auto-detects regions from core_instances.json (same as main_alarm.py).

Usage:
    python main_aom_alarm.py                  # multi-region from core_instances.json
    python main_aom_alarm.py --region cn-south-1  # single region override
"""

import argparse
import json
import logging
import subprocess
from pathlib import Path

from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main-aom-alarm")

OUTPUT_METRIC_PATH = str(Path(INTERMEDIATE_DIR) / "aom_alarm_rules.json")
OUTPUT_EVENT_PATH = str(Path(INTERMEDIATE_DIR) / "aom_event_alarm_rules.json")
CORE_INSTANCES_PATH = str(Path(INTERMEDIATE_DIR) / "core_instances.json")


def _extract_regions_from_core_instances() -> list:
    """Read core_instances.json and extract all unique regions."""
    try:
        with open(CORE_INSTANCES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"core_instances.json not found at {CORE_INSTANCES_PATH}")
        return []

    regions = set()
    for svc, insts in data.get("instances", {}).items():
        for inst in insts:
            region = inst.get("region", "")
            if region:
                regions.add(region)
    return sorted(regions)


def _fetch_aom_rules(region: str, alarm_rule_type: str) -> list:
    """Fetch AOM alarm rules via hcloud CLI for one region and type.

    Args:
        region: Huawei Cloud region ID (e.g., cn-south-1)
        alarm_rule_type: "metric" or "event"

    Returns:
        List of alarm rule dicts.
    """
    result = []
    offset = 0
    limit = 100

    while True:
        cmd = [
            "hcloud", "AOM", "ListMetricOrEventAlarmRule",
            f"--cli-region={region}",
            f"--alarm_rule_type={alarm_rule_type}",
            f"--limit={limit}",
            f"--offset={offset}",
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if proc.returncode != 0:
                logger.error(f"hcloud failed: {proc.stderr[:200]}")
                break

            data = json.loads(proc.stdout)
            rules = data.get("alarm_rules", []) or []
            count = data.get("count", 0)

            for rule in rules:
                rule["region"] = region
                result.append(rule)

            offset += len(rules)
            if len(rules) == 0 or (count and offset >= count):
                break

        except subprocess.TimeoutExpired:
            logger.error(f"hcloud timeout for region={region}, type={alarm_rule_type}")
            break
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            break

    return result


def main(region: str = None):
    # Determine target regions
    if region:
        target_regions = [region]
        logger.info(f"Single-region mode: {region}")
    else:
        target_regions = _extract_regions_from_core_instances()
        if not target_regions:
            logger.warning("No regions found in core_instances.json, falling back to env default")
            target_regions = [None]
        else:
            logger.info(f"Multi-region mode: {len(target_regions)} regions: {target_regions}")

    # Fetch metric-type and event-type rules for each region
    all_metric_rules = []
    all_event_rules = []

    for r in target_regions:
        label = r or "env-default"
        if r is None:
            logger.warning("Cannot fetch AOM rules without a region, skipping")
            continue

        logger.info(f"Fetching AOM metric alarm rules from region: {label}")
        metric_rules = _fetch_aom_rules(r, "metric")
        logger.info(f"  {len(metric_rules)} metric rules")
        all_metric_rules.extend(metric_rules)

        logger.info(f"Fetching AOM event alarm rules from region: {label}")
        event_rules = _fetch_aom_rules(r, "event")
        logger.info(f"  {len(event_rules)} event rules")
        all_event_rules.extend(event_rules)

    logger.info(f"Total AOM metric rules: {len(all_metric_rules)}")
    logger.info(f"Total AOM event rules: {len(all_event_rules)}")

    # Write metric rules
    metric_output = {
        "total_rules": len(all_metric_rules),
        "regions": target_regions,
        "rules": all_metric_rules,
    }
    Path(OUTPUT_METRIC_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_METRIC_PATH, "w", encoding="utf-8") as f:
        json.dump(metric_output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved metric rules to {OUTPUT_METRIC_PATH}")

    # Write event rules
    event_output = {
        "total_rules": len(all_event_rules),
        "regions": target_regions,
        "rules": all_event_rules,
    }
    with open(OUTPUT_EVENT_PATH, "w", encoding="utf-8") as f:
        json.dump(event_output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved event rules to {OUTPUT_EVENT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch AOM alarm rules (multi-region)")
    parser.add_argument("--region", default=None,
                        help="Single region override. If omitted, auto-detects from core_instances.json.")
    args = parser.parse_args()
    main(region=args.region)
