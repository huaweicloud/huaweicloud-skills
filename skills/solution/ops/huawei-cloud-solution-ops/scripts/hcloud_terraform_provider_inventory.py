#!/usr/bin/env python3
"""Build Huawei Cloud Terraform provider resource/data-source inventories."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import hcloud_common

TERRAFORM_DIR = hcloud_common.REFERENCES_DIR / "terraform"
INVENTORY_DIR = TERRAFORM_DIR / "inventories"
RESOURCE_INVENTORY_PATH = INVENTORY_DIR / "provider-resource-inventory.md"
DATA_SOURCE_INVENTORY_PATH = INVENTORY_DIR / "provider-data-source-inventory.md"


def strip_provider_prefix(name: str) -> str:
    """Return provider item name without the huaweicloud prefix."""
    return name.removeprefix("huaweicloud_")


def family_for_name(name: str) -> str:
    """Return the first name token used as provider inventory family."""
    return name.split("_", 1)[0] if name else "unknown"


def discover_items(provider_root: Path, kind: str) -> list[str]:
    """Return provider resource or data-source names from docs markdown files."""
    docs_dir = provider_root / "docs" / kind
    if not docs_dir.exists():
        raise FileNotFoundError(f"provider docs directory not found: {docs_dir}")
    items = []
    for path in sorted(docs_dir.glob("*.md")):
        items.append(strip_provider_prefix(path.stem))
    return sorted(dict.fromkeys(items))


def provider_doc_path(provider_root: Path, kind: str, name: str) -> Path | None:
    """Return the provider Markdown doc path for a resource or data source."""
    docs_dir = provider_root / "docs" / kind
    stripped_name = strip_provider_prefix(name)
    candidates = [
        docs_dir / f"{stripped_name}.md",
        docs_dir / f"huaweicloud_{stripped_name}.md",
        docs_dir / f"{name}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def extract_import_section(text: str) -> str:
    """Return the Markdown Import section body, if present."""
    match = re.search(r"^##\s+Import\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    rest = text[match.end() :]
    next_section = re.search(r"^##\s+", rest, re.MULTILINE)
    return rest[: next_section.start()] if next_section else rest


def extract_force_new_attributes(text: str) -> list[str]:
    """Return documented attributes marked ForceNew in provider Markdown."""
    attributes: list[str] = []
    for match in re.finditer(r"^[ \t]*[*-]\s+`([^`]+)`\s+-\s+\([^)]*ForceNew[^)]*\)", text, re.MULTILINE):
        attributes.append(match.group(1))
    return sorted(dict.fromkeys(attributes))


def extract_sensitive_attribute_hints(text: str) -> list[str]:
    """Return documented attributes that look sensitive or secret-bearing."""
    hints: list[str] = []
    sensitive_name = re.compile(r"(password|passwd|secret|token|private[_-]?key|access[_-]?key)", re.IGNORECASE)
    for match in re.finditer(r"^[ \t]*[*-]\s+`([^`]+)`\s+-\s+\(([^)]*)\)", text, re.MULTILINE):
        name = match.group(1)
        markers = match.group(2)
        if "Sensitive" in markers or sensitive_name.search(name):
            hints.append(name)
    return sorted(dict.fromkeys(hints))


def extract_import_hints(import_section: str) -> list[str]:
    """Return compact import ID hints and terraform import examples."""
    if not import_section:
        return []
    hints: list[str] = []
    for match in re.finditer(r"using (?:the )?`([^`]+)`", import_section, re.IGNORECASE):
        hints.append(match.group(1))
    for line in import_section.splitlines():
        stripped = line.strip()
        if "terraform import" in stripped:
            hints.append(stripped.strip("`"))
    return hints[:10]


def build_doc_signal(provider_root: Path, kind: str, name: str) -> dict[str, Any]:
    """Build docs-first mutability/import/sensitive signals for one provider item."""
    doc_path = provider_doc_path(provider_root, kind, name)
    item_name = strip_provider_prefix(name)
    if doc_path is None:
        return {
            "name": item_name,
            "kind": kind,
            "found": False,
            "doc_path": None,
            "force_new": {"present": False, "attributes": [], "attribute_count": 0},
            "import": {"present": False, "hints": []},
            "sensitive": {"present": False, "attribute_hints": [], "attribute_hint_count": 0},
        }

    text = doc_path.read_text(encoding="utf-8")
    force_new_attributes = extract_force_new_attributes(text)
    import_section = extract_import_section(text)
    sensitive_hints = extract_sensitive_attribute_hints(text)
    return {
        "name": strip_provider_prefix(doc_path.stem),
        "kind": kind,
        "found": True,
        "doc_path": str(doc_path.relative_to(provider_root)),
        "force_new": {
            "present": bool(force_new_attributes) or "ForceNew" in text or "Changing this" in text,
            "attributes": force_new_attributes,
            "attribute_count": len(force_new_attributes),
        },
        "import": {
            "present": bool(import_section),
            "hints": extract_import_hints(import_section),
        },
        "sensitive": {
            "present": bool(sensitive_hints),
            "attribute_hints": sensitive_hints,
            "attribute_hint_count": len(sensitive_hints),
        },
        "planner_notes": [
            "Use ForceNew signals to warn users before changing attributes that may replace resources.",
            "Use Import signals only to draft review steps; do not run terraform import automatically.",
            "Treat sensitive hints as output-handling and variable-file hygiene warnings, not as complete schema truth.",
        ],
    }


def group_items(items: list[str]) -> list[dict[str, Any]]:
    """Group provider item names by their first token."""
    grouped: dict[str, list[str]] = {}
    for item in items:
        grouped.setdefault(family_for_name(item), []).append(item)
    return [{"family": family, "count": len(names), "items": names} for family, names in sorted(grouped.items())]


def read_provider_snapshot(provider_root: Path) -> dict[str, Any]:
    """Return the top changelog version/date for a local provider snapshot."""
    changelog = provider_root / "CHANGELOG.md"
    snapshot = {
        "source": "https://github.com/huaweicloud/terraform-provider-huaweicloud",
        "version": None,
        "date": None,
    }
    if not changelog.exists():
        return snapshot
    match = re.search(r"^##\s+([0-9.]+)\s+\(([^)]+)\)", changelog.read_text(encoding="utf-8"), re.MULTILINE)
    if match:
        snapshot["version"] = match.group(1)
        snapshot["date"] = match.group(2)
    return snapshot


def build_inventory(provider_root: Path, kind: str) -> dict[str, Any]:
    """Build a structured provider inventory from local provider docs."""
    items = discover_items(provider_root, kind)
    groups = group_items(items)
    return {
        "kind": kind,
        "count": len(items),
        "family_count": len(groups),
        "snapshot": read_provider_snapshot(provider_root),
        "groups": groups,
    }


def render_inventory(title: str, description: str, inventory: dict[str, Any]) -> str:
    """Render a provider inventory as Chinese markdown."""
    snapshot = inventory["snapshot"]
    version = snapshot.get("version") or "unknown"
    date = snapshot.get("date") or "unknown"
    source = snapshot["source"]
    lines = [
        f"# {title}",
        "",
        description,
        "",
        f"来源快照：`{source}`，provider changelog 顶部版本 `{version}`，日期 `{date}`。",
        f"覆盖统计：{inventory['count']} 个条目，{inventory['family_count']} 个家族。",
        "",
        "阅读方式：",
        "- 先按家族名查看 provider 是否覆盖某个方向。",
        "- 再结合 `provider-capability-index.md` 判断是否值得进入主线。",
        "- 再结合 `reference-example-inventory.md` 判断是否已经有成型 example。",
        "- 这份文件是生成索引；维护时用 `scripts/hcloud_terraform_provider_inventory.py` 从 provider docs 重建。",
        "",
    ]
    for group in inventory["groups"]:
        lines.append(f"## {group['family']} ({group['count']})")
        for item in group["items"]:
            lines.append(f"- `{item}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_inventories(resource_inventory: dict[str, Any], data_source_inventory: dict[str, Any]) -> None:
    """Write generated provider inventory markdown files."""
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCE_INVENTORY_PATH.write_text(
        render_inventory(
            "Provider Resource Inventory",
            "这份文档把参考仓库 `docs/resources` 中的资源家族完整搬运到 skill 内部，作为 provider 资源覆盖面的总索引。",
            resource_inventory,
        ),
        encoding="utf-8",
    )
    DATA_SOURCE_INVENTORY_PATH.write_text(
        render_inventory(
            "Provider Data Source Inventory",
            "这份文档把参考仓库 `docs/data-sources` 中的 data source 家族完整搬运到 skill 内部，作为 discovery 能力面的总索引。",
            data_source_inventory,
        ),
        encoding="utf-8",
    )


def parse_inventory_items(path: Path) -> set[str]:
    """Return item names already listed in an inventory markdown file."""
    if not path.exists():
        return set()
    return set(re.findall(r"^- `([^`]+)`", path.read_text(encoding="utf-8"), re.MULTILINE))


def compare_inventory(generated: dict[str, Any], existing_path: Path) -> dict[str, Any]:
    """Compare generated inventory names with an existing markdown inventory."""
    generated_items = {item for group in generated["groups"] for item in group["items"]}
    existing_items = parse_inventory_items(existing_path)
    missing = sorted(generated_items - existing_items)
    stale = sorted(existing_items - generated_items)
    return {
        "path": str(existing_path.relative_to(hcloud_common.ROOT)),
        "generated_count": len(generated_items),
        "existing_count": len(existing_items),
        "missing_count": len(missing),
        "stale_count": len(stale),
        "missing_sample": missing[:50],
        "stale_sample": stale[:50],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider-root",
        type=Path,
        required=True,
        help="Explicit local terraform-provider-huaweicloud checkout used for maintenance.",
    )
    parser.add_argument("--write", action="store_true", help="Write provider inventory markdown files.")
    parser.add_argument("--fail-on-drift", action="store_true", help="Return non-zero when committed inventories differ from provider docs.")
    parser.add_argument("--signal-kind", choices=["resources", "data-sources"], help="Return docs-first signals for one or more provider items.")
    parser.add_argument("--signal-name", action="append", default=[], help="Provider item name for --signal-kind, with or without huaweicloud_ prefix.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.signal_name and not args.signal_kind:
        parser.error("--signal-name requires --signal-kind")
    return args


def main() -> int:
    """Build, compare, and optionally write Terraform provider inventories."""
    args = parse_args()
    provider_root = args.provider_root.resolve()
    resource_inventory = build_inventory(provider_root, "resources")
    data_source_inventory = build_inventory(provider_root, "data-sources")
    comparisons = {
        "resources": compare_inventory(resource_inventory, RESOURCE_INVENTORY_PATH),
        "data_sources": compare_inventory(data_source_inventory, DATA_SOURCE_INVENTORY_PATH),
    }
    if args.write:
        write_inventories(resource_inventory, data_source_inventory)
        comparisons = {
            "resources": compare_inventory(resource_inventory, RESOURCE_INVENTORY_PATH),
            "data_sources": compare_inventory(data_source_inventory, DATA_SOURCE_INVENTORY_PATH),
        }
    success = not args.fail_on_drift or all(
        item["missing_count"] == 0 and item["stale_count"] == 0 for item in comparisons.values()
    )
    result = {
        "success": success,
        "provider_root_exists": provider_root.exists(),
        "provider_snapshot": read_provider_snapshot(provider_root),
        "write": args.write,
        "inventories": {
            "resources": {
                "count": resource_inventory["count"],
                "family_count": resource_inventory["family_count"],
                "path": str(RESOURCE_INVENTORY_PATH.relative_to(hcloud_common.ROOT)),
            },
            "data_sources": {
                "count": data_source_inventory["count"],
                "family_count": data_source_inventory["family_count"],
                "path": str(DATA_SOURCE_INVENTORY_PATH.relative_to(hcloud_common.ROOT)),
            },
        },
        "drift": comparisons,
    }
    if args.signal_kind:
        result["doc_signals"] = [
            build_doc_signal(provider_root, args.signal_kind, name)
            for name in (args.signal_name or [])
        ]
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
