#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query DDS resources (document database, standalone script with full-region query; independent of other services).

Usage:
    python query_dds.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Output: <output-dir>/DDS/temp/DDSinstances_<region>_<ts>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, IAM_BASE_REGION, run_regions_concurrent
)  # noqa: E402

SERVICE_DIR = "DDS"
SERVICE_SPEC = {
    "dir": "DDS",
    "cli_service": "DDS",
    "operation": "ListInstances",
    "tsc_interface": "instances"
}
IS_GLOBAL = False


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    spec = SERVICE_SPEC
    eff_region = spec.get("region_override", region)
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], eff_region,
                     spec.get("extra"))
    path = svc_dir / f"{SERVICE_DIR}_{spec['tsc_interface']}_{tag}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    try:
        count = count_items(parse_body(raw))
    except json.JSONDecodeError:
        count = 0
    log(f"[{SERVICE_DIR}] saved {path} ({count} rows)")

    # Flavor table (spec_code -> vcpus/ram): supplies the vCPU/RAM spec columns.
    try:
        f_raw = run_hcloud(hcloud, "DDS", "ListFlavors", eff_region)
        f_path = svc_dir / f"{SERVICE_DIR}_flavors_{tag}_{ts}.json"
        f_path.write_text(f_raw, encoding="utf-8")
        try:
            f_count = count_items(parse_body(f_raw))
        except json.JSONDecodeError:
            f_count = 0
        log(f"[DDS] saved {f_path} ({f_count} flavors)")
    except RuntimeError as exc:
        log(f"[DDS] flavors query failed: {exc}")

    return {"service": "dds", "tsc_interface": spec["tsc_interface"],
            "files": [str(path)], "count": count}


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)

    return {"service": "dds", "regions": results}


def resolve_regions(hcloud, args) -> list[str]:
    explicit = args.regions or (args.region or "")
    if not explicit or explicit.strip().lower() == "auto":
        regions = discover_regions(hcloud)
        if not regions:
            log("Region discovery failed; use --regions to specify explicitly")
            return []
        active = []
        for r in regions:
            ok, why = probe_region(hcloud, r)
            log(f"  Probe {r}: {why} -> {'OK has resources' if ok else 'X skip'}")
            if ok:
                active.append(r)
        return active
    return [r.strip() for r in explicit.split(",") if r.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Query dds resources via KooCLI (multi-region)")
    parser.add_argument("--region", default="", help="Single region (shorthand for --regions)")
    parser.add_argument("--regions", default="auto", help="Region list (comma-separated) or auto (default: auto-discover + probe)")
    parser.add_argument("--output-dir", required=True, help="KooCLI raw output directory")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path")
    args = parser.parse_args()

    hcloud = find_hcloud(args.hcloud_path)
    regions = resolve_regions(hcloud, args)
    if not regions:
        return 1
    result = run_regions(hcloud, regions, Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
