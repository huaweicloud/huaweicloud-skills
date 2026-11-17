#!/usr/bin/env python3
"""
Unified CES alarm rule fetcher.

Combines three former steps into one:
  1. Fetch all alarm rules from CES ListAlarmRules (multi-region, paginated)
  2. For every rule with non-empty resources+dimensions, call
     ListAlarmRuleResources to resolve actual instance IDs (resource_ids)
  3. Split into metric rules and event-type rules (EVENT.SYS / EVENT.CUSTOM)

Outputs:
  - online_alarm_rules.json        — all rules (with resource_ids)
  - online_notification_rules.json — event-type rules only (with resource_ids)

Usage:
    python main_alarm.py                     # multi-region from core_instances.json
    python main_alarm.py --region cn-south-1 # single region override
"""

import argparse
import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from alarm_api import fetch_all_alarm_rules, fetch_alarm_rule_resources
from config import ensure_public_endpoint
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s", force=True)
logger = logging.getLogger("main-alarm")

OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")
NOTIFICATION_OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "online_notification_rules.json")
CORE_INSTANCES_PATH = str(Path(INTERMEDIATE_DIR) / "core_instances.json")

# CES alarm rule types that represent events (not metric alarms)
EVENT_TYPES = {"EVENT.SYS", "EVENT.CUSTOM"}

# Concurrency for ListAlarmRuleResources calls
MAX_WORKERS = 10

# Regions not supported by CES SDK (e.g. 'global' from CDN)
_SKIP_REGIONS = {"global"}


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------

def _extract_regions_from_core_instances() -> list:
    """Read core_instances.json and extract all unique region values."""
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


# ---------------------------------------------------------------------------
# Resource ID resolution (merged from fetch_alarm_resources.py)
# ---------------------------------------------------------------------------

def _normalize_dim(dim):
    """Normalize a dimension item to a dict.

    The CES SDK may return dimensions as JSON strings, dicts, or
    SDK model objects (e.g. DimensionResp with to_dict()).
    """
    if isinstance(dim, dict):
        return dim
    if isinstance(dim, str):
        try:
            return json.loads(dim)
        except (json.JSONDecodeError, ValueError):
            return {}
    if hasattr(dim, "to_dict"):
        return dim.to_dict()
    return {}


def _extract_resource_ids(raw_resources: list) -> list:
    """Extract resource IDs from ListAlarmRuleResources response.

    The CES SDK returns resources as a list of lists, where each inner
    list contains dimension items (dicts or JSON strings):
        [
            ['{"name": "resource_id", "value": "xxx-xxx-xxx"}'],
            ['{"name": "resource_id", "value": "yyy-yyy-yyy"}'],
        ]
    """
    ids = []
    for res in raw_resources:
        if isinstance(res, list):
            for dim in res:
                dim_dict = _normalize_dim(dim)
                value = dim_dict.get("value", "")
                if value:
                    ids.append(value)
        elif isinstance(res, dict):
            for dim in res.get("dimensions", []):
                dim_dict = _normalize_dim(dim)
                value = dim_dict.get("value", "")
                if value:
                    ids.append(value)
    return ids


def _has_non_wildcard_dimensions(rule: dict) -> bool:
    """Check if a rule should be fetched via ListAlarmRuleResources.

    ListAlarmRules returns dimension values as null — the actual resource IDs
    are only available from ListAlarmRuleResources. So we fetch for any rule
    that has non-empty resources (i.e. not a full wildcard).
    """
    resources = rule.get("resources", [])
    return bool(resources)


def _fetch_resource_ids_for_rule(rule: dict) -> list:
    """Fetch resource IDs for a single rule via ListAlarmRuleResources."""
    alarm_id = rule.get("alarm_id", "")
    region = rule.get("region", "")

    if region:
        ensure_public_endpoint(region)

    try:
        raw_resources = fetch_alarm_rule_resources(alarm_id, region)
        return _extract_resource_ids(raw_resources)
    except Exception as e:
        logger.warning(f"  resource fetch failed for {rule.get('name', '')} ({region}): {e}")
        return []


def _enrich_rules_with_resource_ids(rules: list):
    """Fetch resource_ids for all rules that need it (in-place).

    Only rules with non-empty, non-wildcard dimensions are fetched.
    Wildcard rules get an empty resource_ids list.
    """
    rules_to_fetch = [r for r in rules if _has_non_wildcard_dimensions(r)]
    wildcard_count = len(rules) - len(rules_to_fetch)
    logger.info(f"Resource ID fetch: {len(rules_to_fetch)} rules to fetch, "
                f"{wildcard_count} wildcard/skipped")

    if not rules_to_fetch:
        for r in rules:
            r.setdefault("resource_ids", [])
        return

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_resource_ids_for_rule, rule): rule.get("alarm_id", "")
            for rule in rules_to_fetch
        }
        for future in as_completed(futures):
            alarm_id = futures[future]
            try:
                results[alarm_id] = future.result()
            except Exception as e:
                logger.warning(f"  future failed for alarm_id={alarm_id}: {e}")
                results[alarm_id] = []

    # Assign resource_ids to all rules
    fetched_count = 0
    for rule in rules:
        alarm_id = rule.get("alarm_id", "")
        if alarm_id in results:
            rule["resource_ids"] = results[alarm_id]
            if results[alarm_id]:
                fetched_count += 1
        else:
            rule["resource_ids"] = []

    total_ids = sum(len(v) for v in results.values())
    logger.info(f"Resource IDs: {fetched_count} rules with IDs, "
                f"{len(rules_to_fetch) - fetched_count} fetched but empty, "
                f"total {total_ids} IDs")


# ---------------------------------------------------------------------------
# Event rule extraction (merged from main_event.py)
# ---------------------------------------------------------------------------

def _extract_service_from_namespace(namespace: str) -> str:
    """Extract service short name from CES namespace.
    e.g., "SYS.RDS" -> "RDS", "SYS.ECS" -> "ECS"
    """
    if not namespace:
        return ""
    parts = namespace.split(".")
    return parts[1] if len(parts) >= 2 else namespace


def _extract_event_ids(policies: list) -> list:
    """Extract event IDs from alarm rule policies.
    In event-type alarm rules, each policy's metric_name is the event ID.
    """
    event_ids = []
    for policy in (policies or []):
        metric_name = policy.get("metric_name", "")
        if metric_name:
            event_ids.append(metric_name)
    return event_ids


def _split_event_rules(rules: list) -> list:
    """Filter and transform event-type rules from the full rule list."""
    event_rules = []
    for rule in rules:
        rule_type = rule.get("type", "")
        if rule_type not in EVENT_TYPES:
            continue
        if not rule.get("enabled", False):
            continue

        namespace = rule.get("namespace", "")
        service = _extract_service_from_namespace(namespace)
        event_ids = _extract_event_ids(rule.get("policies", []))

        event_rules.append({
            "alarm_id": rule.get("alarm_id", ""),
            "name": rule.get("name", ""),
            "namespace": namespace,
            "service": service,
            "type": rule_type,
            "enabled": rule.get("enabled", False),
            "notification_enabled": rule.get("notification_enabled", False),
            "event_ids": event_ids,
            "resources": rule.get("resources", []),
            "resource_ids": rule.get("resource_ids", []),
            "enterprise_project_id": rule.get("enterprise_project_id", ""),
            "region": rule.get("region", ""),
        })
    return event_rules


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
            target_regions = [r for r in target_regions if r not in _SKIP_REGIONS]
            logger.info(f"Multi-region mode: {len(target_regions)} regions: {target_regions}")

    # Step 1: Fetch all alarm rules from each region
    all_rules = []
    for r in target_regions:
        label = r or "env-default"
        if r:
            ensure_public_endpoint(r)
        logger.info(f"Fetching alarm rules from region: {label}")
        rules = fetch_all_alarm_rules(region=r)
        if not rules:
            logger.warning(f"  No alarm rules from region {label}")
        else:
            logger.info(f"  {len(rules)} alarm rules from region {label}")
        for rule in rules:
            if not rule.get("region"):
                rule["region"] = r or ""
        all_rules.extend(rules)

    logger.info(f"Total alarm rules across all regions: {len(all_rules)}")

    # Step 2: Enrich all rules with resource_ids
    _enrich_rules_with_resource_ids(all_rules)

    # Step 3: Split into metric rules and event rules (enabled only)
    # Disabled rules (both metric and event) are excluded from analysis
    event_rules = _split_event_rules(all_rules)
    event_type_alarm_ids = {r.get("alarm_id", "") for r in all_rules if r.get("type", "") in EVENT_TYPES}
    all_metric_rules = [r for r in all_rules if r.get("alarm_id", "") not in event_type_alarm_ids]
    disabled_metric_count = sum(1 for r in all_metric_rules if not r.get("enabled", False))
    metric_rules = [r for r in all_metric_rules if r.get("enabled", False)]
    logger.info(f"Split: {len(metric_rules)} metric rules (enabled), {disabled_metric_count} metric rules (disabled, excluded), {len(event_rules)} event rules (enabled), {len(event_type_alarm_ids) - len(event_rules)} event rules (disabled, excluded)")

    # Step 4: Write metric rules to online_alarm_rules.json
    output = {
        "total_rules": len(metric_rules),
        "regions": target_regions,
        "rules": metric_rules,
    }
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(metric_rules)} metric rules to {OUTPUT_PATH}")

    # Step 5: Write event rules to online_notification_rules.json
    event_output = {
        "total_rules": len(event_rules),
        "rules": event_rules,
    }
    with open(NOTIFICATION_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(event_output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(event_rules)} event rules to {NOTIFICATION_OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CES alarm rules with resource IDs (unified)")
    parser.add_argument("--region", default=None,
                        help="Single region override (e.g., cn-south-1). "
                             "If omitted, auto-detects all regions from core_instances.json.")
    args = parser.parse_args()
    main(region=args.region)
