#!/usr/bin/env python3
"""Build Terraform asset catalogs for the hcloud-first Huawei Cloud skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import hcloud_common

TERRAFORM_REFERENCES_DIR = hcloud_common.REFERENCES_DIR / "terraform"
TERRAFORM_EXAMPLES_DIR = hcloud_common.ROOT / "examples" / "terraform"
CATALOG_DIR = TERRAFORM_REFERENCES_DIR / "catalog"
EXAMPLE_CATALOG_PATH = CATALOG_DIR / "terraform-example-catalog.json"
REFERENCE_CATALOG_PATH = CATALOG_DIR / "terraform-reference-catalog.json"

STARTER_EXAMPLES = {
    "ecs_stack",
    "ecs_reuse_stack",
    "eip_stack",
    "evs_stack",
    "elb_stack",
    "elb_member_stack",
    "rds_stack",
    "obs_stack",
    "cce_stack",
    "cce_node_pool_stack",
    "nat_snat_stack",
    "dns_stack",
}

SERVICE_ALIASES = {
    "antiddos": "AntiDDoS",
    "aom": "AOM",
    "apig": "APIG",
    "as": "AS",
    "bms": "BMS",
    "cbh": "CBH",
    "cbr": "CBR",
    "cc": "CC",
    "cce": "CCE",
    "cci": "CCI",
    "cdn": "CDN",
    "ces": "CES",
    "coc": "COC",
    "cts": "CTS",
    "dc": "DC",
    "dcs": "DCS",
    "deh": "DEH",
    "dew": "DEW",
    "dms": "DMS",
    "dns": "DNS",
    "ecs": "ECS",
    "eg": "EG",
    "eip": "EIP",
    "elb": "ELB",
    "er": "ER",
    "esw": "ESW",
    "evs": "EVS",
    "fgs": "FGS",
    "hss": "HSS",
    "iam": "IAM",
    "identity_center": "IdentityCenter",
    "ims": "IMS",
    "lts": "LTS",
    "nat": "NAT",
    "obs": "OBS",
    "oms": "OMS",
    "organizations": "Organizations",
    "ram": "RAM",
    "rds": "RDS",
    "rgc": "RGC",
    "rms": "RMS",
    "sdrs": "SDRS",
    "secmaster": "SecMaster",
    "sfs_turbo": "SFS",
    "smn": "SMN",
    "sms": "SMS",
    "swr": "SWR",
    "tms": "TMS",
    "vpc": "VPC",
    "networking": "VPC",
    "vpcep": "VPCEP",
    "vpn": "VPN",
    "waf": "WAF",
}

CATEGORY_BY_SERVICE = {
    "ECS": "compute",
    "BMS": "compute",
    "EVS": "storage",
    "OBS": "storage",
    "SFS": "storage",
    "RDS": "database",
    "DCS": "database",
    "DMS": "platform",
    "CCE": "container",
    "CCI": "container",
    "SWR": "container",
    "EIP": "network",
    "ELB": "network",
    "NAT": "network",
    "DNS": "network",
    "VPC": "network",
    "CDN": "network",
    "VPCEP": "network",
    "VPN": "network",
    "ER": "network",
    "CC": "network",
    "DC": "network",
    "ESW": "network",
    "APIG": "platform",
    "FGS": "platform",
    "WAF": "security",
    "AntiDDoS": "security",
    "CBH": "security",
    "HSS": "security",
    "DEW": "security",
    "SecMaster": "security",
    "IAM": "governance",
    "IdentityCenter": "governance",
    "Organizations": "governance",
    "RAM": "governance",
    "RGC": "governance",
    "RMS": "governance",
    "TMS": "governance",
    "CBR": "governance",
    "CTS": "governance",
    "CES": "observability",
    "LTS": "observability",
    "AOM": "observability",
    "COC": "operations",
    "SMN": "operations",
    "SMS": "migration",
    "OMS": "migration",
    "SDRS": "migration",
    "IMS": "image",
    "AS": "compute",
    "DEH": "compute",
    "EG": "platform",
}


def normalize_token(value: str) -> str:
    """Return a loose lowercase token for matching."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def token_parts(value: str) -> list[str]:
    """Return normalized underscore-separated parts for exact alias matching."""
    normalized = normalize_token(value)
    return [part for part in normalized.split("_") if part]


def alias_matches_parts(alias: str, parts: list[str]) -> bool:
    """Return True when an alias matches complete normalized parts."""
    alias_parts = token_parts(alias)
    if not alias_parts:
        return False
    if len(alias_parts) == 1:
        return alias_parts[0] in parts
    window = len(alias_parts)
    return any(parts[index : index + window] == alias_parts for index in range(0, len(parts) - window + 1))


def read_summary(path: Path) -> str:
    """Return the first useful markdown line from a README."""
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    for index, line in enumerate(lines):
        text = line.strip()
        if in_frontmatter:
            if index > 0 and text == "---":
                in_frontmatter = False
            continue
        if not text or text.startswith("#"):
            continue
        return text
    return ""


def services_for_example(example_id: str, tf_files: list[Path]) -> list[str]:
    """Infer Huawei Cloud services from an example id and Terraform resources."""
    services: set[str] = set()
    parts = token_parts(example_id)
    for alias, service in SERVICE_ALIASES.items():
        if alias_matches_parts(alias, parts):
            services.add(service)

    resource_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in tf_files)
    for match in re.finditer(r'\b(?:resource|data)\s+"huaweicloud_([a-z0-9_]+)"', resource_text):
        prefix = match.group(1).split("_", 1)[0]
        service = SERVICE_ALIASES.get(prefix)
        if service:
            services.add(service)
    return sorted(services)


def category_for_example(services: list[str], example_id: str) -> str:
    """Return the primary category for an example."""
    if "reuse" in example_id:
        return "reuse"
    if "migration" in example_id:
        return "migration"
    for service in services:
        category = CATEGORY_BY_SERVICE.get(service)
        if category:
            return category
    return "advanced"


def intents_for_example(example_id: str, services: list[str], category: str) -> list[str]:
    """Return compact intent tags for routing."""
    intents = {"terraform", "iac", "create"}
    normalized_id = normalize_token(example_id)
    if "reuse" in normalized_id:
        intents.add("reuse_existing")
    if "security_group" in normalized_id or "secgroup" in normalized_id:
        intents.add("security_group")
    if "peering" in normalized_id:
        intents.add("peering")
    if "addon" in normalized_id:
        intents.add("addon")
    if "coredns" in normalized_id:
        intents.add("coredns")
    if "turbo" in normalized_id:
        intents.add("turbo")
    if "partition" in normalized_id:
        intents.add("partition")
    if "replica" in normalized_id:
        intents.add("read_replica")
    if "ha" in normalized_id:
        intents.add("high_availability")
    if "mysql" in normalized_id:
        intents.add("mysql")
    if "postgresql" in normalized_id:
        intents.add("postgresql")
    if "sqlserver" in normalized_id:
        intents.add("sqlserver")
    if "cdn" in normalized_id and "dns" in normalized_id:
        intents.add("static_site")
    if "node_pool" in normalized_id:
        intents.add("node_pool")
    if "member" in normalized_id:
        intents.add("backend_member")
    if "snat" in normalized_id:
        intents.add("outbound")
    if "dnat" in normalized_id:
        intents.add("inbound")
    intents.add(category)
    intents.update(service.lower() for service in services)
    return sorted(intents)


def complexity_for_example(example_id: str, services: list[str]) -> str:
    """Return low/medium/high complexity for routing."""
    if example_id in STARTER_EXAMPLES and len(services) <= 3:
        return "low"
    if len(services) >= 4 or any(token in example_id for token in ("member", "node_pool", "organizations", "identity_center")):
        return "high"
    return "medium"


def build_example_catalog(examples_dir: Path = TERRAFORM_EXAMPLES_DIR) -> dict[str, Any]:
    """Build a Terraform example catalog."""
    examples: list[dict[str, Any]] = []
    for example_dir in sorted(path for path in examples_dir.iterdir() if path.is_dir()):
        tf_files = sorted(example_dir.glob("*.tf"))
        if not tf_files:
            continue
        services = services_for_example(example_dir.name, tf_files)
        category = category_for_example(services, example_dir.name)
        files = sorted(path.name for path in example_dir.iterdir() if path.is_file())
        examples.append(
            {
                "id": example_dir.name,
                "path": example_dir.relative_to(hcloud_common.ROOT).as_posix(),
                "category": category,
                "services": services,
                "intent": intents_for_example(example_dir.name, services, category),
                "recommended_for": read_summary(example_dir / "README.md"),
                "complexity": complexity_for_example(example_dir.name, services),
                "default_route": example_dir.name in STARTER_EXAMPLES,
                "requires_existing_resources": "reuse" in example_dir.name,
                "entry_files": [name for name in ("versions.tf", "provider.tf", "variables.tf", "main.tf", "outputs.tf") if name in files],
                "files": files,
                "validation": ["fmt", "init-backend-false", "validate"],
            }
        )
    return {
        "schema_version": 1,
        "description": "Terraform example catalog. Use this for routing; do not browse every example by default.",
        "example_count": len(examples),
        "default_route_count": sum(1 for item in examples if item["default_route"]),
        "examples": examples,
    }


def reference_category(path: Path) -> str:
    """Return a category for one Terraform reference file."""
    parts = set(path.parts)
    name = path.name
    if "inventories" in parts:
        return "inventory"
    if "tests" in parts:
        return "test-reference"
    if name in {
        "provider-auth.md",
        "provider-validation.md",
        "generation-guardrails.md",
        "operations.md",
        "discovery-workflow.md",
        "interop-with-hcloud.md",
        "service-variant-guide.md",
        "data-source-selection-guide.md",
        "troubleshooting.md",
        "roadmap.md",
        "terraform-assets.md",
    }:
        return "core"
    if name == "source-skill.md":
        return "source-archive"
    return "advanced"


def build_reference_catalog(references_dir: Path = TERRAFORM_REFERENCES_DIR) -> dict[str, Any]:
    """Build a Terraform reference catalog."""
    references = []
    for path in sorted(references_dir.rglob("*.md")):
        relative = path.relative_to(hcloud_common.ROOT)
        category = reference_category(path.relative_to(references_dir))
        references.append(
            {
                "id": path.stem,
                "path": relative.as_posix(),
                "category": category,
                "default_route": category == "core",
                "summary": read_summary(path),
            }
        )
    return {
        "schema_version": 1,
        "description": "Terraform reference catalog. Load core references first; use inventories only on explicit provider coverage questions.",
        "reference_count": len(references),
        "default_route_count": sum(1 for item in references if item["default_route"]),
        "references": references,
    }


def write_catalogs(example_catalog: dict[str, Any], reference_catalog: dict[str, Any]) -> None:
    """Write catalog JSON files."""
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_CATALOG_PATH.write_text(json.dumps(example_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REFERENCE_CATALOG_PATH.write_text(json.dumps(reference_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples-dir", type=Path, default=TERRAFORM_EXAMPLES_DIR, help="Terraform examples directory.")
    parser.add_argument("--references-dir", type=Path, default=TERRAFORM_REFERENCES_DIR, help="Terraform references directory.")
    parser.add_argument("--write", action="store_true", help="Write catalog JSON files to references/terraform/catalog.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build Terraform catalogs."""
    args = parse_args()
    example_catalog = build_example_catalog(args.examples_dir)
    reference_catalog = build_reference_catalog(args.references_dir)
    result = {
        "success": True,
        "example_catalog": example_catalog,
        "reference_catalog": reference_catalog,
        "write": args.write,
        "outputs": {
            "examples": str(EXAMPLE_CATALOG_PATH),
            "references": str(REFERENCE_CATALOG_PATH),
        },
    }
    if args.write:
        write_catalogs(example_catalog, reference_catalog)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
