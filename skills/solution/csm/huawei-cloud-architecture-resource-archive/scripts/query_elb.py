#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query ELB resources (standalone script: load balancers + backend pools + members, independent of other services).

Flow:
  1. ELB ListLoadBalancers → ELB/temp/ELB_loadbalancers_<region>_<ts>.json
  2. ListPools per LB (--loadbalancer_id.1= array parameter) → ELB/temp/ELB_pools_<LB-name>_<region>_<ts>.json
  3. ListMembers per Pool → ELB/temp/ELB_members_<pool_id>_<region>_<ts>.json
     (pools/members are used for "downstream inferred": ELB → backend servers)

Usage:
    python query_elb.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query LBs + Pools + Members per region.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import find_hcloud, run_hcloud, count_items, parse_body, timestamp, log, run_regions_concurrent  # noqa: E402

SERVICE_DIR = "ELB"
SERVICE_SPEC = {"cli_service": "ELB", "operation": "ListLoadBalancers",
                "tsc_interface": "loadbalancers"}


def run(hcloud: Path, region: str, out_root: Path) -> dict:
    spec = SERVICE_SPEC
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "elb", "tsc_interface": spec["tsc_interface"], "files": []}

    raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], region)
    path = svc_dir / f"{SERVICE_DIR}_{spec['tsc_interface']}_{region}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    result["files"].append(str(path))
    try:
        count = count_items(parse_body(raw))
    except json.JSONDecodeError:
        count = 0
    result["count"] = count
    log(f"[ELB] saved {path} ({count} rows)")

    # ListPools per LB -> ListMembers per Pool
    try:
        data = json.loads(raw)
        lbs = data.get("loadbalancers") or data.get("load_balancers") or []
        for lb in lbs:
            lbid = lb.get("id")
            if not lbid:
                continue
            try:
                pools_raw = run_hcloud(hcloud, "ELB", "ListPools", region,
                                       ["--loadbalancer_id.1=" + lbid])  # KooCLI array parameter with .1 index
                ppath = svc_dir / f"ELB_pools_{lb.get('name', lbid)}_{region}_{ts}.json"
                ppath.write_text(pools_raw, encoding="utf-8")
                result["files"].append(str(ppath))
                try:
                    pdata = json.loads(pools_raw)
                    for pool in pdata.get("pools") or []:
                        pid = pool.get("id")
                        if not pid:
                            continue
                        try:
                            mem_raw = run_hcloud(hcloud, "ELB", "ListMembers", region,
                                                 ["--pool_id=" + pid])
                            mpath = svc_dir / f"ELB_members_{pid}_{region}_{ts}.json"
                            mpath.write_text(mem_raw, encoding="utf-8")
                            result["files"].append(str(mpath))
                        except RuntimeError as exc:
                            log(f"  [ELB] pool {pid} members query failed: {exc}")
                except json.JSONDecodeError:
                    pass
            except RuntimeError as exc:
                log(f"  [ELB] lb {lbid} pools query failed: {exc}")
    except json.JSONDecodeError:
        pass

    return result


def run_regions(hcloud, regions: list[str], out_root: Path) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root)

    return {"service": "elb", "regions": results}


def resolve_regions(hcloud, args) -> list[str]:
    from common import discover_regions, probe_region
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
    parser = argparse.ArgumentParser(description="Query ELB loadbalancers/pools/members via KooCLI (multi-region)")
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