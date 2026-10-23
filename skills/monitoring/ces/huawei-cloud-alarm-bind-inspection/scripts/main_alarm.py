#!/usr/bin/env python3
"""
Fetch all alarm rules from CES (Cloud Eye Service) for the current customer.
Single-customer mode: uses AK/SK from environment variables.

Multi-region mode (default): reads all unique regions from core_instances.json
and fetches alarm rules from each region. Each rule is tagged with its source
region so downstream bind_analysis can filter by instance region.

Usage:
    python main_alarm.py                     # multi-region from core_instances.json
    python main_alarm.py --region cn-south-1 # single region override
"""

import argparse
import json
import logging
from pathlib import Path

from alarm_api import fetch_all_alarm_rules
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main-alarm")

OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")
CORE_INSTANCES_PATH = str(Path(INTERMEDIATE_DIR) / "core_instances.json")


def _extract_regions_from_core_instances() -> list:
    """Read core_instances.json and extract all unique region values."""
    try:
        with open(CORE_INSTANCES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"core_instances.json not found at {CORE_INSTANCES_PATH}")
        return []

    regions = set()
    instances = data.get("instances", {})
    for svc, insts in instances.items():
        for inst in insts:
            region = inst.get("region", "")
            if region:
                regions.add(region)
    return sorted(regions)


def main(region: str = None):
    """
    Fetch alarm rules from CES.

    Args:
        region: If provided, fetch from this single region only.
                If None, auto-detect all regions from core_instances.json
                and fetch from each.
    """
    # Determine target regions
    if region:
        target_regions = [region]
        logger.info(f"Single-region mode: {region}")
    else:
        target_regions = _extract_regions_from_core_instances()
        if not target_regions:
            logger.warning("No regions found in core_instances.json, falling back to env default")
            target_regions = [None]  # let build_ces_client use HW_REGION_NAME env
        else:
            logger.info(f"Multi-region mode: {len(target_regions)} regions: {target_regions}")

    # Fetch from each region
    all_rules = []
    for r in target_regions:
        label = r or "env-default"
        logger.info(f"Fetching alarm rules from region: {label}")
        rules = fetch_all_alarm_rules(region=r)
        if not rules:
            logger.warning(f"  No alarm rules from region {label}")
        else:
            logger.info(f"  {len(rules)} alarm rules from region {label}")
        # Tag each rule with its source region
        for rule in rules:
            if "region" not in rule or not rule.get("region"):
                rule["region"] = r or ""
        all_rules.extend(rules)

    logger.info(f"Total alarm rules across all regions: {len(all_rules)}")

    output = {
        "total_rules": len(all_rules),
        "regions": target_regions,
        "rules": all_rules,
    }

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch alarm rules from CES (multi-region)")
    parser.add_argument("--region", default=None,
                        help="Single region override (e.g., cn-south-1). "
                             "If omitted, auto-detects all regions from core_instances.json.")
    args = parser.parse_args()
    main(region=args.region)
