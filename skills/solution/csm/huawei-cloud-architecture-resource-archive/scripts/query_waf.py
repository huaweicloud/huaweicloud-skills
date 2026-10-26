#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query WAF Web Application Firewall resources (regional, standalone script with full-region query; independent of other services).

Sub-resources:
  - ListHost       WAF shared-mode protected domain (primary resource)
  - ListInstance   WAF dedicated-mode instance

Usage:
    python query_waf.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query WAF domains + instances per region.
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

SERVICE_DIR = "WAF"


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query WAF protected domains + dedicated instances for a single region, save to <out_root>/WAF/temp/."""
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "waf", "files": []}

    # 1. WAF shared-mode protected domains (ListHost)
    try:
        raw = run_hcloud(hcloud, "WAF", "ListHost", region)
        path = svc_dir / f"WAF_hosts_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        result["files"].append(str(path))
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        result["count"] = count
        log(f"[WAF] protected domains saved {path} ({count} rows)")
    except RuntimeError as exc:
        log(f"[WAF] ListHost query failed: {exc}")
        result["count"] = 0

    # 2. WAF dedicated-mode instances (ListInstance)
    try:
        inst_raw = run_hcloud(hcloud, "WAF", "ListInstance", region)
        inst_path = svc_dir / f"WAF_instances_{tag}_{ts}.json"
        inst_path.write_text(inst_raw, encoding="utf-8")
        result["files"].append(str(inst_path))
        try:
            inst_count = count_items(parse_body(inst_raw))
        except json.JSONDecodeError:
            inst_count = 0
        log(f"[WAF] dedicated instances saved {inst_path} ({inst_count} rows)")
    except RuntimeError as exc:
        log(f"[WAF] ListInstance query failed: {exc}")

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "waf", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query WAF hosts + instances via KooCLI (multi-region)")
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
