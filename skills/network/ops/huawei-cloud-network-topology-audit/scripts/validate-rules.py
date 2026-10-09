#!/usr/bin/env python3
"""
Validate the network audit rules YAML file.

Checks:
  - All required fields present
  - Rule IDs are unique
  - Severity is one of the five valid values
  - Resource types are from the allowed list
  - Condition is non-empty

Usage:
    python3 validate-rules.py rules/network-audit-rules.yaml
"""

import sys
import yaml

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}

ALLOWED_RESOURCE_TYPES = {
    "elb_listener", "elb_backend", "eip", "nat", "nat_snat", "nat_dnat",
    "security_group", "route_table", "vpc", "subnet",
    "ecs_nic", "rds_instance",
    "cce_cluster", "cce_node", "cce_service", "cce_ingress",
    "dcs_instance"
}


def validate(path):
    errors = []
    warnings = []

    try:
        with open(path, "r") as f:
            rules = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"YAML parse error: {e}")
        sys.exit(1)

    if not isinstance(rules, list):
        print(f"ERROR: Expected a list of rules, got {type(rules).__name__}")
        sys.exit(1)

    print(f"Loaded {len(rules)} rules from {path}")

    seen_ids = set()

    for i, rule in enumerate(rules):
        prefix = f"Rule {i + 1} (index {i})"

        if not isinstance(rule, dict):
            errors.append(f"{prefix}: Expected dict, got {type(rule).__name__}")
            continue

        # Check required fields
        required_fields = ["id", "resource_type", "condition", "severity", "description"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"{prefix}: Missing required field '{field}'")
            elif not rule[field] and rule[field] is not False:
                errors.append(f"{prefix}: Field '{field}' is empty")

        if "id" in rule and rule["id"]:
            rid = rule["id"]
            if rid in seen_ids:
                errors.append(f"{prefix}: Duplicate ID '{rid}'")
            seen_ids.add(rid)

            # Validate ID format
            if not rid.startswith("NET-"):
                errors.append(f"{prefix}: ID '{rid}' should start with 'NET-'")

            parts = rid.split("-")
            if len(parts) != 3:
                warnings.append(f"{prefix}: ID '{rid}' does not follow NET-CAT-NNN format")

        # Validate severity
        if "severity" in rule:
            sev = rule["severity"]
            if sev not in ALLOWED_SEVERITIES:
                errors.append(f"{prefix}: Invalid severity '{sev}'. Must be one of: {', '.join(sorted(ALLOWED_SEVERITIES))}")

        # Validate resource_type
        if "resource_type" in rule:
            rts = rule["resource_type"]
            if not isinstance(rts, list):
                errors.append(f"{prefix}: resource_type should be a list, got {type(rts).__name__}")
            else:
                for rt in rts:
                    if rt not in ALLOWED_RESOURCE_TYPES:
                        warnings.append(f"{prefix}: resource_type '{rt}' not in known types list. Add to ALLOWED_RESOURCE_TYPES if valid.")

    # Summary
    print(f"\nValidation Summary:")
    print(f"  Total rules: {len(rules)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\nErrors:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nFAILED: {len(errors)} error(s) found")
        sys.exit(1)
    else:
        print(f"\nPASSED: All rules valid")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = "rules/network-audit-rules.yaml"
    else:
        path = sys.argv[1]

    validate(path)