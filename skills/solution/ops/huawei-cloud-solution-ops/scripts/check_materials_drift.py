#!/usr/bin/env python3
"""Check whether curated references may lag behind raw KooCLI materials."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_common

ROOT = hcloud_common.ROOT
DEFAULT_MAPPING = ROOT / "references" / "materials-sources.json"


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a file."""
    return hcloud_common.load_json(path)


def check_mapping(mapping_path: Path = DEFAULT_MAPPING) -> dict[str, Any]:
    """Return drift findings for mapped reference and material files."""
    mapping = load_json(mapping_path)
    findings = []
    for item in mapping.get("mappings", []):
        reference = ROOT / item["reference"]
        materials = [ROOT / material for material in item.get("materials", [])]
        missing = [str(path.relative_to(ROOT)) for path in [reference, *materials] if not path.exists()]
        newer_materials = []
        if not missing and reference.exists():
            reference_mtime = reference.stat().st_mtime
            newer_materials = [
                str(material.relative_to(ROOT))
                for material in materials
                if material.stat().st_mtime > reference_mtime
            ]
        findings.append(
            {
                "reference": item["reference"],
                "materials": item.get("materials", []),
                "missing": missing,
                "newer_materials": newer_materials,
                "status": "missing" if missing else ("drift" if newer_materials else "ok"),
            }
        )
    return {
        "success": all(item["status"] == "ok" for item in findings),
        "mapping": str(mapping_path.relative_to(ROOT)),
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING), help="materials-sources.json path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Run the materials drift check."""
    args = parse_args()
    result = check_mapping(Path(args.mapping))
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
