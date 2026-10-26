#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query DCAAS cloud direct connect resources and their sub-resources (regional, standalone script with full-region query; independent of other services).

Sub-resources (5, corresponding to the 5 DCAAS types):
  - ListDirectConnects         direct connect
  - ListHostedDirectConnects   hosted direct connect (managed physical connection)
  - ListVirtualGateways        virtual gateway
  - ListVirtualInterfaces      virtual interface
  - ListGlobalDcGateways       global DC gateway

Usage:
    python query_dcaas.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query the 5 DCAAS sub-resource types per region.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, run_regions_concurrent
)  # noqa: E402

SERVICE_DIR = "DCAAS"

# DCAAS sub-resource query spec: (tsc_interface, cli_operation, list_key)
DCAAS_SUB_RESOURCES = [
    ("direct_connects",     "ListDirectConnects",       "direct_connects"),
    ("hosted_direct_connects", "ListHostedDirectConnects", "hosted_direct_connects"),
    ("virtual_gateways",    "ListVirtualGateways",      "virtual_gateways"),
    ("virtual_interfaces",  "ListVirtualInterfaces",    "virtual_interfaces"),
    ("global_dc_gateways",  "ListGlobalDcGateways",     "global_dc_gateways"),
]


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query the 5 DCAAS sub-resource types for a single region, save to <out_root>/DCAAS/temp/."""
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "dcaas", "files": []}
    total_count = 0

    for tsc_iface, operation, _list_key in DCAAS_SUB_RESOURCES:
        try:
            raw = run_hcloud(hcloud, "DC", operation, region)
            path = svc_dir / f"DCAAS_{tsc_iface}_{tag}_{ts}.json"
            path.write_text(raw, encoding="utf-8")
            result["files"].append(str(path))
            try:
                count = count_items(parse_body(raw))
            except json.JSONDecodeError:
                count = 0
            total_count += count
            log(f"[DCAAS] {tsc_iface} saved {path} ({count} rows)")
        except RuntimeError as exc:
            log(f"[DCAAS] {operation} query failed: {exc}")

    result["count"] = total_count
    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "dcaas", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query DCAAS direct connects + virtual gateways/interfaces via KooCLI (multi-region)")
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
