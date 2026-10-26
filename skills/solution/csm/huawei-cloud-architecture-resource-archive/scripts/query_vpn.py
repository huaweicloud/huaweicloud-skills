#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query VPN resources and their sub-resources (regional, standalone script with full-region query; independent of other services).

Sub-resources:
  - ListVgws             VPN gateway (primary resource)
  - ListVpnConnections   VPN connection (queried per gateway, --vgw_id=)
  - ListCgws             customer gateway
  - ListP2cVgws          P2C VPN gateway (Point-to-Cloud)

Usage:
    python query_vpn.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query VPN gateways/connections/customer gateways/P2C gateways per region.
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

SERVICE_DIR = "VPN"


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query VPN gateways/connections/customer gateways/P2C gateways for a single region, save to <out_root>/VPN/temp/."""
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "vpn", "files": []}

    # 1. VPN gateways (primary resource)
    try:
        raw = run_hcloud(hcloud, "VPN", "ListVgws", region)
        path = svc_dir / f"VPN_vpn_gateways_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        result["files"].append(str(path))
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        log(f"[VPN] gateways saved {path} ({count} rows)")

        # 2. Query VPN connections per gateway
        try:
            data = json.loads(raw)
            gateways = data.get("vpn_gateways") or []
            for gw in gateways:
                gw_id = gw.get("id")
                if not gw_id:
                    continue
                gw_name = gw.get("name", gw_id)
                try:
                    conn_raw = run_hcloud(hcloud, "VPN", "ListVpnConnections", region,
                                          ["--vgw_id=" + gw_id])
                    conn_path = svc_dir / f"VPN_vpn_connections_{gw_name}_{tag}_{ts}.json"
                    conn_path.write_text(conn_raw, encoding="utf-8")
                    result["files"].append(str(conn_path))
                    try:
                        conn_count = count_items(parse_body(conn_raw))
                    except json.JSONDecodeError:
                        conn_count = 0
                    log(f"  [VPN] connections {gw_name}: {conn_count} rows")
                except RuntimeError as exc:
                    log(f"  [VPN] {gw_name} connections query failed: {exc}")
        except json.JSONDecodeError:
            pass
    except RuntimeError as exc:
        log(f"[VPN] ListVgws query failed: {exc}")

    # 3. Customer gateways (ListCgws)
    try:
        cgw_raw = run_hcloud(hcloud, "VPN", "ListCgws", region)
        cgw_path = svc_dir / f"VPN_customer_gateways_{tag}_{ts}.json"
        cgw_path.write_text(cgw_raw, encoding="utf-8")
        result["files"].append(str(cgw_path))
        try:
            cgw_count = count_items(parse_body(cgw_raw))
        except json.JSONDecodeError:
            cgw_count = 0
        log(f"[VPN] customer gateways saved {cgw_path} ({cgw_count} rows)")
    except RuntimeError as exc:
        log(f"[VPN] ListCgws query failed: {exc}")

    # 4. P2C VPN gateways
    try:
        p2c_raw = run_hcloud(hcloud, "VPN", "ListP2cVgws", region)
        p2c_path = svc_dir / f"VPN_p2c_vpn_gateways_{tag}_{ts}.json"
        p2c_path.write_text(p2c_raw, encoding="utf-8")
        result["files"].append(str(p2c_path))
        try:
            p2c_count = count_items(parse_body(p2c_raw))
        except json.JSONDecodeError:
            p2c_count = 0
        log(f"[VPN] P2C gateways saved {p2c_path} ({p2c_count} rows)")
    except RuntimeError as exc:
        log(f"[VPN] ListP2cVgws query failed: {exc}")

    return result


def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                label: str | None = None) -> dict:
    results = run_regions_concurrent(run, hcloud, regions, out_root, label=label)
    return {"service": "vpn", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query VPN gateways/connections/peer-gateways/P2C via KooCLI (multi-region)")
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
