#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified query driver for template-based services (config-driven, standalone runnable).

This module replaces 18 near-identical `query_<svc>.py` template scripts (each ~65-110 lines
differing only in SERVICE_DIR / SERVICE_SPEC / IS_GLOBAL) with one config dictionary + generic
`run` / `run_regions` / `main`.

Two access modes:
  1. importlib alias (used by query_resources.py): on import this module registers one
     `sys.modules["query_<svc>"]` alias per service in SERVICE_SPECS. Each alias exposes
     `run(hcloud, region, out_root, label=...)` and `run_regions(hcloud, regions, out_root, ...)`
     bound to that service's spec — so `importlib.import_module("query_vpc")` behaves exactly
     like the old standalone file, with zero changes in query_resources.py.
  2. Standalone CLI: `python query_svc_registry.py --service vpc --regions auto --output-dir ...`

Kept separate (NOT merged here) because they carry service-specific logic:
  cce/cci/cnad/dcaas/dli/dns/elb/er/geminidb/nat/vpn/waf/workspace/sfs/mrs/cloudtable/cc2/cfw/bgp/dds/obs/rms
(e.g. CCI namespace iteration, OBS via RMS, workspace products, multi-interface NAT/DNS/ER/VPN).
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, IAM_BASE_REGION, run_regions_concurrent
)  # noqa: E402

# ── Config-driven service specs (dir / cli_service / operation / tsc_interface) ──
# Each entry maps the query_resources.py service key to its spec. `extra` holds fixed
# CLI flags; `region_override` pins the API region (e.g. CDN ListDomains only exists in cn-north-1);
# `global: True` marks account-level services queried once (tag = "global").
SERVICE_SPECS: dict[str, dict] = {
    "cdn":   {"dir": "CDN",   "cli_service": "CDN",     "operation": "ListDomains",          "region_override": "cn-north-1", "tsc_interface": "domains",           "global": True},
    "ecs":   {"dir": "ECS",   "cli_service": "ECS",     "operation": "ListServersDetails",   "tsc_interface": "servers"},
    "eip":   {"dir": "EIP",   "cli_service": "EIP",     "operation": "ListPublicips",        "tsc_interface": "publicips"},
    "eps":   {"dir": "EPS",   "cli_service": "EPS",     "operation": "ListEnterpriseProject", "tsc_interface": "enterprise_projects", "global": True},
    "geip":  {"dir": "GEIP",  "cli_service": "GEIP",    "operation": "ListGlobalEips",       "tsc_interface": "global_eip_list",   "global": True},
    "live":  {"dir": "LIVE",  "cli_service": "Live",    "operation": "ShowDomain",           "tsc_interface": "domains"},
    "dcs":   {"dir": "DCS",   "cli_service": "DCS",     "operation": "ListInstances",        "tsc_interface": "instances"},
    "dms":   {"dir": "DMS",   "cli_service": "Kafka",   "operation": "ListInstances",        "extra": ["--engine=kafka"],          "tsc_interface": "instances"},
    "gaussdb": {"dir": "GAUSSDB", "cli_service": "GaussDBforopenGauss", "operation": "ListInstances", "tsc_interface": "instances"},
    "taurusdb": {"dir": "TAURUSDB", "cli_service": "GaussDB", "operation": "ListGaussMySqlInstances", "tsc_interface": "instances"},
    "rds":   {"dir": "RDS",   "cli_service": "RDS",     "operation": "ListInstances",        "tsc_interface": "instances"},
    "networkacl": {"dir": "NETWORKACL", "cli_service": "VPC", "operation": "ListFirewall",   "tsc_interface": "firewalls"},
    "peering": {"dir": "PEERING", "cli_service": "VPC", "operation": "ListVpcPeerings",      "tsc_interface": "vpc_peerings"},
    "routetable": {"dir": "ROUTETABLE", "cli_service": "VPC", "operation": "ListRouteTables", "tsc_interface": "route_tables"},
    "securitygroup": {"dir": "SECURITYGROUP", "cli_service": "VPC", "operation": "ListSecurityGroups", "tsc_interface": "security_groups"},
    "subnet": {"dir": "SUBNET", "cli_service": "VPC",   "operation": "ListSubnets",           "tsc_interface": "subnets"},
    "vpc":   {"dir": "VPC",   "cli_service": "VPC",     "operation": "ListVpcs",             "tsc_interface": "vpcs"},
    "vpcep": {"dir": "VPCEP", "cli_service": "VPCEP",   "operation": "ListEndpoints",        "tsc_interface": "endpoints"},
}

_MODULE = sys.modules[__name__]


def _query_for(service: str):
    """Return a per-service query function bound to the given spec."""
    spec = SERVICE_SPECS[service]

    def query(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
        """Query one region; save to <out_root>/<DIR>/temp/; return a summary dict."""
        eff_region = spec.get("region_override", region)
        tag = label or region
        svc_dir = out_root / spec["dir"] / "temp"
        svc_dir.mkdir(parents=True, exist_ok=True)
        ts = timestamp()
        raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], eff_region,
                         spec.get("extra"))
        path = svc_dir / f"{spec['dir']}_{spec['tsc_interface']}_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        try:
            count = count_items(parse_body(raw))
        except json.JSONDecodeError:
            count = 0
        log(f"[{spec['dir']}] saved {path} ({count} rows)")
        return {"service": spec["dir"].lower(), "tsc_interface": spec["tsc_interface"],
                "files": [str(path)], "count": count}

    def run_regions(hcloud: Path, regions: list[str], out_root: Path,
                    label: str | None = None) -> dict:
        """Query per region concurrently; returns {region: result} (same interface as old files)."""
        results = run_regions_concurrent(query, hcloud, regions, out_root, label=label)
        return {"service": spec["dir"].lower(), "regions": results}

    return query, run_regions


# ── Register per-service alias modules so importlib.import_module("query_<svc>") works ──
for _svc in SERVICE_SPECS:
    _query, _run_regions = _query_for(_svc)
    _alias = types.SimpleNamespace(
        __name__=f"query_{_svc}",
        SERVICE_DIR=SERVICE_SPECS[_svc]["dir"],
        SERVICE_SPEC=SERVICE_SPECS[_svc],
        IS_GLOBAL=SERVICE_SPECS[_svc].get("global", False),
        run=_query,
        run_regions=_run_regions,
    )
    sys.modules[f"query_{_svc}"] = _alias


# Standalone default service (overridden by --service)
_DEFAULT_SERVICE = "vpc"


def resolve_regions(hcloud, args) -> list[str]:
    """Parse region list; --regions auto / default -> auto-discover + probe."""
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
    parser = argparse.ArgumentParser(
        description="Query a template-based Huawei Cloud service via KooCLI (config-driven, multi-region)")
    parser.add_argument("--service", default=_DEFAULT_SERVICE,
                        help=f"Service key (one of {sorted(SERVICE_SPECS)})")
    parser.add_argument("--region", default="", help="Single region (shorthand for --regions)")
    parser.add_argument("--regions", default="auto",
                        help="Region list (comma-separated) or auto (default: auto-discover + probe)")
    parser.add_argument("--output-dir", required=True, help="KooCLI raw output directory")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path")
    args = parser.parse_args()

    spec = SERVICE_SPECS[args.service]
    hcloud = find_hcloud(args.hcloud_path)
    if spec.get("global"):
        # Global resource: once per account (cli-region uses the real region, tag = global)
        _query, _ = _query_for(args.service)
        result = {"service": args.service,
                  "regions": {"global": _query(hcloud, IAM_BASE_REGION, Path(args.output_dir), label="global")}}
    else:
        regions = resolve_regions(hcloud, args)
        if not regions:
            return 1
        _query, _run_regions = _query_for(args.service)
        result = _run_regions(hcloud, regions, Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
