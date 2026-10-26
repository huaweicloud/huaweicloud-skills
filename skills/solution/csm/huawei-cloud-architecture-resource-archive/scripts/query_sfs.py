#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query SFS elastic file system resources and their sub-types (regional, standalone script with full-region query).

3 file system types are required:
  - SFS   Turbo   → SFS  ListShareFileSystems   (list_key: shares)
  - SFS3  3.0     → SFS3 ListFileSystems         (list_key: file_systems)
  - EFS   elastic → EFS  ListFileSystems         (list_key: file_systems)

Usage:
    python query_sfs.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, run_regions_concurrent)  # noqa: E402

SERVICE_DIR = "SFS"

# Sub-resource types: (tsc_interface, cli_service, operation, list_key)
# KooCLI exposes only SFSTurbo (service name "SFSTurbo", operation "ListShares").
# SFS3 / EFS have no standalone KooCLI service (no "SFS3"/"EFS" in `hcloud --help`),
# so only the SFS Turbo query is attempted; the other two stay zero-row.
SFS_SUB_RESOURCES = [
    ("sfs_shares",       "SFSTurbo", "ListShares", "shares"),
]


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "sfs", "files": []}
    total = 0

    for tsc_iface, cli_svc, operation, _key in SFS_SUB_RESOURCES:
        try:
            raw = run_hcloud(hcloud, cli_svc, operation, region)
            path = svc_dir / f"SFS_{tsc_iface}_{tag}_{ts}.json"
            path.write_text(raw, encoding="utf-8")
            result["files"].append(str(path))
            count = count_items(parse_body(raw))
            total += count
            log(f"[SFS] {tsc_iface} saved {path} ({count} rows)")
        except RuntimeError as exc:
            log(f"[SFS] {cli_svc} {operation} query failed: {exc}")

    result["count"] = total
    return result


def run_regions(hcloud, regions, out_root, label=None):
    return {"service": "sfs", "regions": run_regions_concurrent(run, hcloud, regions, out_root, label=label)}


def resolve_regions(hcloud, args):
    explicit = args.regions or (args.region or "")
    if not explicit or explicit.strip().lower() == "auto":
        regions = discover_regions(hcloud)
        if not regions:
            return []
        return [r for r in regions if probe_region(hcloud, r)[0]]
    return [r.strip() for r in explicit.split(",") if r.strip()]


def main():
    parser = argparse.ArgumentParser(description="Query SFS/SFS3/EFS file systems via KooCLI")
    parser.add_argument("--region", default="")
    parser.add_argument("--regions", default="auto")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--hcloud-path", default="")
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
