#!/usr/bin/env python3
"""Compare local Billing/BSS planner operations with official reference skills."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import hcloud_billing_readonly
import hcloud_common

BUNDLED_BASELINE_PATH = (
    hcloud_common.REFERENCES_DIR / "billing" / "operation-gap-baseline.json"
)
UPSTREAM_REPOSITORY = "https://github.com/huaweicloud/huaweicloud-skills"

OPERATION_RE = re.compile(r"\b(?:List|Show)[A-Za-z0-9]+\b")
SCRIPT_HEADING_RE = re.compile(r"^###\s+([a-z0-9_]+)\.py\s+[—-]\s+(.+)$", re.MULTILINE)
MATRIX_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$")
PRICING_OPERATION_SCRIPTS = {"list_on_demand_resource_ratings.py", "list_rate_on_period_detail.py"}


def skill_relative(path: Path) -> str:
    """Return a skill-relative path when possible, otherwise the caller path."""
    try:
        return str(path.relative_to(hcloud_common.ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    """Return UTF-8 text from a local reference file."""
    return path.read_text(encoding="utf-8")


def snake_to_operation_name(script_name: str) -> str | None:
    """Convert a BSS list_*/show_* script filename to a KooCLI operation name."""
    stem = script_name.removesuffix(".py")
    if not stem.startswith(("list_", "show_")):
        return None
    parts = [part for part in stem.split("_") if part]
    if not parts:
        return None
    return "".join(part[:1].upper() + part[1:] for part in parts)


def parse_scout_operations(text: str) -> set[str]:
    """Extract BSS List*/Show* operations from billing-scout command references."""
    return {match.group(0) for match in OPERATION_RE.finditer(text)}


def parse_business_guide(text: str) -> dict[str, Any]:
    """Extract BSS operations, pricing helpers, and matrix rows from the business query guide."""
    operations: dict[str, dict[str, Any]] = {}
    pricing_helpers: list[dict[str, str]] = []
    pricing_operations: set[str] = set()

    for match in SCRIPT_HEADING_RE.finditer(text):
        script = f"{match.group(1)}.py"
        title = match.group(2).strip()
        operation = snake_to_operation_name(script)
        if operation:
            operations[operation] = {"script": script, "title": title}
            if script in PRICING_OPERATION_SCRIPTS:
                pricing_operations.add(operation)
        elif script.startswith("inquiry_"):
            pricing_helpers.append({"script": script, "title": title})

    pricing_matrix = []
    in_matrix = False
    for line in text.splitlines():
        if line.strip() == "## Pricing Support Matrix":
            in_matrix = True
            continue
        if in_matrix and line.startswith("## "):
            break
        if not in_matrix or not line.startswith("|"):
            continue
        if "---" in line or "Cloud Service" in line:
            continue
        row = MATRIX_ROW_RE.match(line)
        if not row:
            continue
        service, billing_mode, on_demand, period = [item.strip() for item in row.groups()]
        pricing_matrix.append(
            {
                "service": service,
                "billing_mode": billing_mode,
                "on_demand": on_demand,
                "period": period,
            }
        )

    return {
        "operations": operations,
        "pricing_helpers": pricing_helpers,
        "pricing_operations": pricing_operations,
        "pricing_matrix": pricing_matrix,
    }


def parse_business_script_dir(script_dir: Path) -> dict[str, dict[str, str]]:
    """Extract BSS operation names from official business query script filenames."""
    operations: dict[str, dict[str, str]] = {}
    if not script_dir.exists():
        return operations
    for path in sorted(script_dir.glob("*.py")):
        operation = snake_to_operation_name(path.name)
        if operation:
            operations[operation] = {"script": path.name}
    return operations


def local_operations() -> dict[str, dict[str, Any]]:
    """Return local hcloud_billing_readonly operation metadata indexed by KooCLI operation."""
    aliases_by_key: dict[str, list[str]] = {}
    for alias, target in hcloud_billing_readonly.OPERATION_ALIASES.items():
        aliases_by_key.setdefault(target, []).append(alias)

    result: dict[str, dict[str, Any]] = {}
    for key, metadata in hcloud_billing_readonly.OPERATIONS.items():
        operation = str(metadata.get("title") or "")
        if not operation:
            continue
        result[operation] = {
            "local_key": key,
            "aliases": sorted(aliases_by_key.get(key, [])),
            "method": metadata.get("method"),
            "path": metadata.get("path"),
            "permission": metadata.get("permission"),
        }
    return result


def add_operation_source(index: dict[str, dict[str, Any]], operation: str, source: str, details: dict[str, Any] | None = None) -> None:
    """Record one official reference source for an operation."""
    entry = index.setdefault(operation, {"operation": operation, "sources": []})
    source_entry = {"source": source}
    if details:
        source_entry.update(details)
    entry["sources"].append(source_entry)


def classify_missing_operation(operation: str, sources: list[dict[str, Any]], pricing_operations: set[str]) -> dict[str, str]:
    """Return priority and category for a missing official BSS operation."""
    source_names = {str(source.get("source")) for source in sources}
    if operation in pricing_operations:
        return {"priority": "P1", "category": "pricing_api_gap"}
    if "billing_scout_related_commands" in source_names:
        return {"priority": "P1", "category": "billing_scout_gap"}
    return {"priority": "P2", "category": "business_support_query_gap"}


def build_reference_baseline(
    scout_related_commands: Path,
    business_bss_guide: Path,
    business_bss_script_dir: Path | None = None,
) -> dict[str, Any]:
    """Normalize explicit upstream BSS reference files into a portable baseline."""
    scout_ops = parse_scout_operations(read_text(scout_related_commands))
    guide = parse_business_guide(read_text(business_bss_guide))
    guide_ops = guide["operations"]
    script_ops = (
        parse_business_script_dir(business_bss_script_dir)
        if business_bss_script_dir is not None
        else {}
    )

    official_index: dict[str, dict[str, Any]] = {}
    for operation in scout_ops:
        add_operation_source(
            official_index,
            operation,
            "billing_scout_related_commands",
        )
    for operation, details in guide_ops.items():
        add_operation_source(
            official_index,
            operation,
            "business_support_query_guide",
            details,
        )
    for operation, details in script_ops.items():
        add_operation_source(
            official_index,
            operation,
            "business_support_query_scripts",
            details,
        )

    pricing_operations = sorted(guide["pricing_operations"])
    return {
        "schema_version": 1,
        "description": "Portable normalized BSS operation baseline for local gap analysis.",
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "source_files": [
                "skills/bss/billing/huawei-cloud-billing-scout/references/related-commands.md",
                "skills/bss/billing/huawei-cloud-business-tf-support/references/bss/guide.md",
                "skills/bss/billing/huawei-cloud-business-tf-support/scripts/bss",
            ],
        },
        "official_operations": [
            official_index[operation] for operation in sorted(official_index)
        ],
        "statistics": {
            "billing_scout_operation_count": len(scout_ops),
            "business_query_operation_count": len(set(guide_ops) | set(script_ops)),
            "pricing_operation_count": len(pricing_operations),
        },
        "pricing_operations": pricing_operations,
        "pricing_helpers": guide["pricing_helpers"],
        "pricing_matrix": guide["pricing_matrix"],
    }


def load_reference_baseline(path: Path) -> dict[str, Any]:
    """Load and validate the portable BSS operation baseline."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported billing operation baseline schema.")
    if not isinstance(data.get("official_operations"), list):
        raise ValueError("Billing operation baseline has no official_operations list.")
    return data


def write_reference_baseline(path: Path, baseline: dict[str, Any]) -> None:
    """Write a normalized portable baseline for future standalone audits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_gap_report(
    *,
    baseline_path: Path = BUNDLED_BASELINE_PATH,
    scout_related_commands: Path | None = None,
    business_bss_guide: Path | None = None,
    business_bss_script_dir: Path | None = None,
) -> dict[str, Any]:
    """Build a local-only BSS operation gap report from bundled or explicit inputs."""
    explicit_sources = any(
        path is not None
        for path in (
            scout_related_commands,
            business_bss_guide,
            business_bss_script_dir,
        )
    )
    required_source_paths = (
        scout_related_commands,
        business_bss_guide,
    )
    if explicit_sources and any(path is None for path in required_source_paths):
        return {
            "success": False,
            "planning_only": True,
            "error": "incomplete_reference_inputs",
            "required_together": [
                "scout_related_commands",
                "business_bss_guide",
            ],
        }

    paths_to_check = (
        [
            path
            for path in (
                scout_related_commands,
                business_bss_guide,
                business_bss_script_dir,
            )
            if path is not None
        ]
        if explicit_sources
        else [baseline_path]
    )
    missing_files = [
        skill_relative(path)
        for path in paths_to_check
        if not path.exists()
    ]
    if missing_files:
        return {
            "success": False,
            "planning_only": True,
            "error": "missing_reference_files",
            "missing_files": missing_files,
        }

    if explicit_sources:
        baseline = build_reference_baseline(
            scout_related_commands,
            business_bss_guide,
            business_bss_script_dir,
        )
        reference_sources = {
            "mode": "explicit_maintenance_inputs",
            "billing_scout_related_commands": skill_relative(
                scout_related_commands
            ),
            "business_support_query_guide": skill_relative(
                business_bss_guide
            ),
            "business_support_query_scripts": (
                skill_relative(business_bss_script_dir)
                if business_bss_script_dir is not None
                else None
            ),
        }
    else:
        try:
            baseline = load_reference_baseline(baseline_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return {
                "success": False,
                "planning_only": True,
                "error": "invalid_bundled_baseline",
                "baseline": skill_relative(baseline_path),
                "details": str(exc),
            }
        reference_sources = {
            "mode": "bundled_snapshot",
            "baseline": skill_relative(baseline_path),
            "upstream": baseline.get("upstream", {}),
        }

    official_index = {
        str(entry["operation"]): entry
        for entry in baseline["official_operations"]
        if isinstance(entry, dict) and entry.get("operation")
    }

    local_index = local_operations()
    local_operation_names = set(local_index)
    official_operation_names = set(official_index)
    supported = sorted(official_operation_names & local_operation_names)
    missing = []
    pricing_operations = set(baseline.get("pricing_operations", []))
    for operation in sorted(official_operation_names - local_operation_names):
        sources = official_index[operation]["sources"]
        classification = classify_missing_operation(operation, sources, pricing_operations)
        missing.append(
            {
                "operation": operation,
                "priority": classification["priority"],
                "category": classification["category"],
                "sources": sources,
            }
        )

    local_extra = sorted(local_operation_names - official_operation_names)
    return {
        "success": True,
        "planning_only": True,
        "execution_boundary": "local_reference_diff_only_no_hcloud_no_credentials",
        "reference_sources": reference_sources,
        "local": {
            "operation_count": len(local_index),
            "operations": [
                {"operation": operation, **local_index[operation]}
                for operation in sorted(local_index)
            ],
        },
        "official": {
            "combined_operation_count": len(official_operation_names),
            "billing_scout_operation_count": baseline.get("statistics", {}).get(
                "billing_scout_operation_count",
                0,
            ),
            "business_query_operation_count": baseline.get(
                "statistics",
                {},
            ).get("business_query_operation_count", 0),
            "pricing_operation_count": len(pricing_operations),
            "pricing_helper_count": len(baseline.get("pricing_helpers", [])),
            "pricing_helpers": baseline.get("pricing_helpers", []),
            "pricing_matrix": baseline.get("pricing_matrix", []),
        },
        "coverage": {
            "complete": not missing,
            "supported_operation_count": len(supported),
            "missing_operation_count": len(missing),
            "local_extra_operation_count": len(local_extra),
            "supported_operations": supported,
            "missing_operations": missing,
            "local_extra_operations": local_extra,
        },
        "next_actions": [
            "Review P1 gaps before adding new planner operations.",
            "Add only read-only List*/Show* BSS operations with explicit required fields, pagination, and redaction boundaries.",
            "Keep inquiry_elb.py, inquiry_nat.py, and inquiry_dcs.py as design references; do not import their AK/SK collection or direct SDK execution pattern.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BUNDLED_BASELINE_PATH,
        help="Bundled normalized baseline used by default.",
    )
    parser.add_argument(
        "--scout-related-commands",
        type=Path,
        help="Explicit upstream billing-scout related-commands.md for maintenance refresh.",
    )
    parser.add_argument(
        "--business-bss-guide",
        type=Path,
        help="Explicit upstream business-support BSS guide for maintenance refresh.",
    )
    parser.add_argument(
        "--business-bss-script-dir",
        type=Path,
        help="Explicit upstream business-support BSS script directory.",
    )
    parser.add_argument(
        "--write-baseline",
        type=Path,
        help="Write a normalized baseline from the explicit upstream inputs.",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    source_inputs = (
        args.scout_related_commands,
        args.business_bss_guide,
        args.business_bss_script_dir,
    )
    if any(source_inputs) and (
        args.scout_related_commands is None
        or args.business_bss_guide is None
    ):
        parser.error(
            "--scout-related-commands and --business-bss-guide must be provided together."
        )
    if args.write_baseline and not any(source_inputs):
        parser.error("--write-baseline requires explicit upstream inputs.")
    return args


def main() -> int:
    """Run the BSS operation gap audit."""
    args = parse_args()
    if args.write_baseline:
        missing_paths = [
            path
            for path in (
                args.scout_related_commands,
                args.business_bss_guide,
                args.business_bss_script_dir,
            )
            if path is not None and not path.exists()
        ]
        if missing_paths:
            result = {
                "success": False,
                "planning_only": True,
                "error": "missing_reference_files",
                "missing_files": [skill_relative(path) for path in missing_paths],
            }
        else:
            baseline = build_reference_baseline(
                args.scout_related_commands,
                args.business_bss_guide,
                args.business_bss_script_dir,
            )
            write_reference_baseline(args.write_baseline, baseline)
            result = build_gap_report(baseline_path=args.write_baseline)
            result["baseline_written"] = skill_relative(args.write_baseline)
    else:
        result = build_gap_report(
            baseline_path=args.baseline,
            scout_related_commands=args.scout_related_commands,
            business_bss_guide=args.business_bss_guide,
            business_bss_script_dir=args.business_bss_script_dir,
        )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
