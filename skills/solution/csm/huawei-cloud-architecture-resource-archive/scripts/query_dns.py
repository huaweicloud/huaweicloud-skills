#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query DNS resources and their sub-resources (regional, standalone script with full-region query; independent of other services).

Sub-resources:
  - ListPublicZones      public domain zones (global, but queried per region for KooCLI compatibility)
  - ListPrivateZones     private domain zones (regional)
  - ListEndpoints        outbound endpoints (regional)
  - ListResolverRules    resolver rules (regional)

Usage:
    python query_dns.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query public/private domains + endpoints + resolver rules per region.
Note: public domains are global resources; multi-region queries return the same result, deduplicated by region in the convert stage.
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

SERVICE_DIR = "DNS"

# sub-resource -> (KooCLI operation, tsc_interface, extra_args)
SUB_OPS = [
    ("ListPublicZones",   "public_zones",   []),
    ("ListPrivateZones",  "private_zones",  ["--type=private"]),
    ("ListEndpoints",     "endpoints",      ["--direction=outbound"]),
    ("ListResolverRules", "resolver_rules", []),
]


def _extract_zone_ids(raw: str) -> list[str]:
    """Extract zone ids from a ListPrivateZones response."""
    data = parse_body(raw)
    if not isinstance(data, dict):
        return []
    return [_text_id(z.get("id")) for z in (data.get("zones") or [])]


def _text_id(v) -> str:
    return str(v).strip() if v else ""


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query DNS public/private zones + endpoints + resolver rules for a single region, save to <out_root>/DNS/temp/.

    After listing private zones, each zone is individually queried with ShowPrivateZone
    to capture its associated VPC routers (needed for downstream inference).
    """
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "dns", "files": []}

    for op, tsc, extra in SUB_OPS:
        try:
            raw = run_hcloud(hcloud, "DNS", op, region, extra)
        except RuntimeError as exc:
            log(f"[DNS/{op}] query failed: {exc}")
            continue
        path = svc_dir / f"{SERVICE_DIR}_{tsc}_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        result["files"].append(str(path))
        log(f"[DNS/{op}] saved {path} ({count} rows)")

        # After listing private zones, fetch each zone's VPC association (routers).
        if op == "ListPrivateZones":
            for zid in _extract_zone_ids(raw):
                try:
                    detail = run_hcloud(hcloud, "DNS", "ShowPrivateZone", region,
                                        ["--zone_id=" + zid])
                except RuntimeError as exc:
                    log(f"[DNS/ShowPrivateZone {zid}] query failed: {exc}")
                    continue
                dpath = svc_dir / f"{SERVICE_DIR}_private_zone_routers_{zid}_{tag}_{ts}.json"
                dpath.write_text(detail, encoding="utf-8")
                result["files"].append(str(dpath))
                log(f"[DNS/ShowPrivateZone {zid}] saved {dpath}")

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "dns", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query DNS zones/endpoints/resolver-rules via KooCLI (multi-region)")
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
