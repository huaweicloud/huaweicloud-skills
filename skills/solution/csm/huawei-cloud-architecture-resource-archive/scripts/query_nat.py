#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query NAT gateways and their sub-resources (regional, standalone script with full-region query; independent of other services).

Flow:
  1. NAT ListNatGateways → NAT/temp/NAT_nat_gateways_<region>_<ts>.json
  2. ListNatGatewaySnatRules per gateway (--nat_gateway_id=) → NAT/temp/NAT_snat_rules_<gateway-name>_<region>_<ts>.json
  3. ListNatGatewayDnatRules per gateway (--nat_gateway_id=) → NAT/temp/NAT_dnat_rules_<gateway-name>_<region>_<ts>.json
     (snat_rules/dnat_rules are used for "downstream inferred": NAT → associated subnets/EIPs)

Usage:
    python query_nat.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query NAT gateways + SNAT/DNAT rules per region.
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

SERVICE_DIR = "NAT"
SERVICE_SPEC = {"cli_service": "NAT", "operation": "ListNatGateways",
                "tsc_interface": "nat_gateways"}


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query NAT gateways + SNAT/DNAT rules for a single region, save to <out_root>/NAT/temp/."""
    spec = SERVICE_SPEC
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "nat", "tsc_interface": spec["tsc_interface"], "files": []}

    # 1. Query NAT gateways
    raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], region)
    path = svc_dir / f"{SERVICE_DIR}_{spec['tsc_interface']}_{tag}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    result["files"].append(str(path))
    try:
        count = count_items(parse_body(raw))
    except json.JSONDecodeError:
        count = 0
    result["count"] = count
    log(f"[NAT] saved {path} ({count} rows)")

    # 2. Query SNAT/DNAT rules per gateway
    try:
        data = json.loads(raw)
        gateways = data.get("nat_gateways") or []
        for gw in gateways:
            gw_id = gw.get("id")
            if not gw_id:
                continue
            gw_name = gw.get("name", gw_id)
            # SNAT rules
            try:
                snat_raw = run_hcloud(hcloud, "NAT", "ListNatGatewaySnatRules", region,
                                      ["--nat_gateway_id.1=" + gw_id])
                snat_path = svc_dir / f"NAT_snat_rules_{gw_name}_{tag}_{ts}.json"
                snat_path.write_text(snat_raw, encoding="utf-8")
                result["files"].append(str(snat_path))
                try:
                    snat_count = count_items(parse_body(snat_raw))
                except json.JSONDecodeError:
                    snat_count = 0
                log(f"  [NAT] SNAT rules {gw_name}: {snat_count} rows")
            except RuntimeError as exc:
                log(f"  [NAT] {gw_name} SNAT rules query failed: {exc}")
            # DNAT rules
            try:
                dnat_raw = run_hcloud(hcloud, "NAT", "ListNatGatewayDnatRules", region,
                                      ["--nat_gateway_id.1=" + gw_id])
                dnat_path = svc_dir / f"NAT_dnat_rules_{gw_name}_{tag}_{ts}.json"
                dnat_path.write_text(dnat_raw, encoding="utf-8")
                result["files"].append(str(dnat_path))
                try:
                    dnat_count = count_items(parse_body(dnat_raw))
                except json.JSONDecodeError:
                    dnat_count = 0
                log(f"  [NAT] DNAT rules {gw_name}: {dnat_count} rows")
            except RuntimeError as exc:
                log(f"  [NAT] {gw_name} DNAT rules query failed: {exc}")
    except json.JSONDecodeError:
        pass

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "nat", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query NAT gateways + SNAT/DNAT rules via KooCLI (multi-region)")
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
