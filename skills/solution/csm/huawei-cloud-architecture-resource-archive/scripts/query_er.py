#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query Enterprise Router (ER) and its sub-resources (regional, standalone script with full-region query; independent of other services).

Flow:
  1. ER ListInstances → ER/temp/ER_instances_<region>_<ts>.json
  2. ListRouteTables per router (--instance_id=) → ER/temp/ER_route_tables_<router-name>_<region>_<ts>.json
  3. ListAttachments per router (--instance_id=) → ER/temp/ER_attachments_<router-name>_<region>_<ts>.json
     (route_tables/attachments are used for "downstream inferred": ER → associated VPC/VPN etc.)

Usage:
    python query_er.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query ERs + route tables + attachments per region.
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

SERVICE_DIR = "ER"
SERVICE_SPEC = {"cli_service": "ER", "operation": "ListEnterpriseRouters",
                "tsc_interface": "instances"}


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query enterprise routers + route tables + attachments for a single region, save to <out_root>/ER/temp/."""
    spec = SERVICE_SPEC
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "er", "tsc_interface": spec["tsc_interface"], "files": []}

    # 1. Query enterprise routers
    raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], region)
    path = svc_dir / f"{SERVICE_DIR}_{spec['tsc_interface']}_{tag}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    result["files"].append(str(path))
    try:
        count = count_items(parse_body(raw))
    except json.JSONDecodeError:
        count = 0
    result["count"] = count
    log(f"[ER] saved {path} ({count} rows)")

    # 2. Query route tables + attachments per router
    try:
        data = json.loads(raw)
        instances = data.get("instances") or []
        for inst in instances:
            inst_id = inst.get("id")
            if not inst_id:
                continue
            inst_name = inst.get("name", inst_id)
            # Route tables (KooCLI requires --er_id for the router instance)
            try:
                rt_raw = run_hcloud(hcloud, "ER", "ListRouteTables", region,
                                    ["--er_id=" + inst_id])
                rt_path = svc_dir / f"ER_route_tables_{inst_name}_{tag}_{ts}.json"
                rt_path.write_text(rt_raw, encoding="utf-8")
                result["files"].append(str(rt_path))
                try:
                    rt_count = count_items(parse_body(rt_raw))
                except json.JSONDecodeError:
                    rt_count = 0
                log(f"  [ER] route tables {inst_name}: {rt_count} rows")
            except RuntimeError as exc:
                log(f"  [ER] {inst_name} route tables query failed: {exc}")
            # Attachments (KooCLI requires --er_id for the router instance)
            try:
                att_raw = run_hcloud(hcloud, "ER", "ListAttachments", region,
                                     ["--er_id=" + inst_id])
                att_path = svc_dir / f"ER_attachments_{inst_name}_{tag}_{ts}.json"
                att_path.write_text(att_raw, encoding="utf-8")
                result["files"].append(str(att_path))
                try:
                    att_count = count_items(parse_body(att_raw))
                except json.JSONDecodeError:
                    att_count = 0
                log(f"  [ER] attachments {inst_name}: {att_count} rows")
            except RuntimeError as exc:
                log(f"  [ER] {inst_name} attachments query failed: {exc}")
    except json.JSONDecodeError:
        pass

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "er", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query ER instances/route-tables/attachments via KooCLI (multi-region)")
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
