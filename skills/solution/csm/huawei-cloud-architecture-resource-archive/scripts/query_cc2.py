#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query CC2.0 cloud connect resources (global service, queried once per account; independent of other services).

Sub-resources:
  - ListCloudConnections       cloud connection (primary resource)
  - ListInterRegionBandwidths  inter-region bandwidth
  - ListBandwidthPackages      bandwidth package (global interconnect bandwidth package)

Usage:
    python query_cc2.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Global service: queried once per account (cli-region uses cn-north-1, tag = global).
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

SERVICE_DIR = "CC2"
# CC2.0 global service, uses cn-north-1 region (same as CCAAS)
CC2_REGION = "cn-north-1"
IS_GLOBAL = True


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query CC2.0 cloud connections + inter-region bandwidths + bandwidth packages, save to <out_root>/CC2/temp/."""
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "cc2", "files": []}

    # 1. Cloud connections (ListCloudConnections)
    try:
        raw = run_hcloud(hcloud, "CC", "ListCloudConnections", CC2_REGION)
        path = svc_dir / f"CC2_cloud_connections_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        result["files"].append(str(path))
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        result["count"] = count
        log(f"[CC2] cloud connections saved {path} ({count} rows)")
    except RuntimeError as exc:
        log(f"[CC2] ListCloudConnections query failed: {exc}")
        result["count"] = 0

    # 2. Inter-region bandwidths (ListInterRegionBandwidths)
    try:
        irb_raw = run_hcloud(hcloud, "CC", "ListInterRegionBandwidths", CC2_REGION)
        irb_path = svc_dir / f"CC2_inter_region_bandwidths_{tag}_{ts}.json"
        irb_path.write_text(irb_raw, encoding="utf-8")
        result["files"].append(str(irb_path))
        try:
            irb_count = count_items(parse_body(irb_raw))
        except json.JSONDecodeError:
            irb_count = 0
        log(f"[CC2] inter-region bandwidths saved {irb_path} ({irb_count} rows)")
    except RuntimeError as exc:
        log(f"[CC2] ListInterRegionBandwidths query failed: {exc}")

    # 3. Bandwidth packages (ListBandwidthPackages)
    try:
        bwp_raw = run_hcloud(hcloud, "CC", "ListBandwidthPackages", CC2_REGION)
        bwp_path = svc_dir / f"CC2_bandwidth_packages_{tag}_{ts}.json"
        bwp_path.write_text(bwp_raw, encoding="utf-8")
        result["files"].append(str(bwp_path))
        try:
            bwp_count = count_items(parse_body(bwp_raw))
        except json.JSONDecodeError:
            bwp_count = 0
        log(f"[CC2] bandwidth packages saved {bwp_path} ({bwp_count} rows)")
    except RuntimeError as exc:
        log(f"[CC2] ListBandwidthPackages query failed: {exc}")

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "cc2", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query CC2.0 cloud connections + bandwidths via KooCLI (global)")
    parser.add_argument("--region", default="", help="Single region (shorthand for --regions)")
    parser.add_argument("--regions", default="auto", help="Region list (comma-separated) or auto (default: auto-discover + probe)")
    parser.add_argument("--output-dir", required=True, help="KooCLI raw output directory")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path")
    args = parser.parse_args()

    hcloud = find_hcloud(args.hcloud_path)
    if IS_GLOBAL:
        # Global resource: once per account (tag = global)
        result = {"service": "cc2", "regions": {"global": run(hcloud, IAM_BASE_REGION, Path(args.output_dir), label="global")}}
    else:
        regions = resolve_regions(hcloud, args)
        if not regions:
            return 1
        result = run_regions(hcloud, regions, Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
