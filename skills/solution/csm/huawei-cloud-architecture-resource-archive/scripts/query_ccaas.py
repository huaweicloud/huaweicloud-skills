#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query CCAAS cloud connections and their sub-resources (global service, queried once per account; independent of other services).

Sub-resources:
  - ListCloudConnections           cloud connection (primary resource)
  - ListInterRegionBandwidths      inter-region bandwidth (sub-resource of cloud connection, used for [subtype] relationship)
  - ListBandwidthPackages          bandwidth package
  - ListNetworkInstances           network instance
  - ListCloudConnectionRoutes      cloud connection route

Usage:
    python query_ccaas.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]
Global service: queried once per account (cli-region uses the real region, file/row region tag = global)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body, timestamp, log,  # noqa: E402
                    IAM_BASE_REGION, run_regions_concurrent
)

SERVICE_DIR = "CCAAS"
IS_GLOBAL = True

# sub-resource -> (KooCLI operation, tsc_interface, response list key)
SUB_OPS = [
    ("ListCloudConnections",      "cloud_connections",       "cloud_connections"),
    ("ListInterRegionBandwidths", "inter_region_bandwidths", "inter_region_bandwidths"),
    ("ListBandwidthPackages",     "bandwidth_packages",      "bandwidth_packages"),
    ("ListNetworkInstances",      "network_instances",       "network_instances"),
    ("ListCloudConnectionRoutes", "cloud_connection_routes", "routes"),
]


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "ccaas", "files": []}
    for op, tsc, key in SUB_OPS:
        try:
            raw = run_hcloud(hcloud, "CC", op, region)
        except RuntimeError as exc:
            log(f"[CCAAS/{op}] query failed: {exc}")
            continue
        path = svc_dir / f"{SERVICE_DIR}_{tsc}_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        result["files"].append(str(path))
        log(f"[CCAAS/{op}] saved {path} ({count} rows)")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Query CCAAS cloud connections + sub-resources (global)")
    parser.add_argument("--output-dir", required=True, help="KooCLI raw output directory")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path")
    args = parser.parse_args()
    hcloud = find_hcloud(args.hcloud_path)
    result = run(hcloud, IAM_BASE_REGION, Path(args.output_dir), label="global")
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())