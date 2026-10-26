#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource query dispatcher: region discovery → RMS/VPC probing → concurrent invocation of per-resource-type scripts.

Design (split by resource type, independent of each other):
  - Each resource type has an independent script scripts/query_<service>.py with full-region
    query capability (--regions auto, per-region query, filenames carry the region); can run standalone:
      query_cce(cluster+node+K8s sub-resources) / query_vpc / query_subnet / query_ecs /
      query_obs / query_elb(LB+pool+member) / query_geip / query_rms / query_cdn /
      query_ccaas / query_eps
  - This script: probes the region list once → **concurrently** invokes run_regions() of each
    script (isolated with try/except), so one service failure does not affect others;
    results are merged by convert/marker into the full-region marker table
  - Global resources (geip/cdn/ccaas/eps) are queried once per account, region tag = global

Concurrency design (two levels):
  - Service-level concurrency: different resource types (VPC/ECS/CCE/OBS...) queried at the same
    time, controlled by --workers
  - Region-level concurrency: different regions of the same resource type queried at the same time,
    implemented by run_regions() of each script via common.run_regions_concurrent(),
    controlled by --region-workers
  - I/O bound (subprocess calling hcloud, waiting on API responses) → ThreadPoolExecutor

Multi-region flow (default auto):
  1. IAM KeystoneListProjects discovers the regions enabled for the account
  2. Probe per region: RMS CollectAllResourcesSummary (supported only in some regions) → otherwise VPC/ECS fallback
  3. Concurrently run all services only for regions that have resources

Usage:
    python query_resources.py \
      --account <account-name> \
      [--regions auto | cn-north-4,ap-southeast-3]   # default auto
      [--region cn-north-4]                          # single region (backward compatible)
      [--services "cce,vpc,ecs"] \
      [--workers 8]                                 # service-level concurrency (0=auto, 1=serial)
      [--region-workers 5]                          # region-level concurrency (0=auto, 1=serial)
      [--output-dir <root dir>]
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, discover_regions, probe_region, timestamp, log,
                     IAM_BASE_REGION, is_auth_error)  # noqa: E402
import check_koocli  # preflight dependency self-check  # noqa: E402
import query_svc_registry  # registers sys.modules aliases for template services (cdn/ecs/vpc/...)  # noqa: E402,F401

# Service -> standalone script module (loaded via importlib in isolation)
SERVICE_MODULES = {
    "cce":    "query_cce",
    "vpc":    "query_vpc",
    "subnet": "query_subnet",
    "obs":    "query_obs",
    "rms":    "query_rms",
    "ecs":    "query_ecs",
    "eip":    "query_eip",
    "geip":   "query_geip",
    "cdn":    "query_cdn",
    "ccaas":  "query_ccaas",
    "elb":    "query_elb",
    "eps":    "query_eps",
    "routetable": "query_routetable",
    "securitygroup": "query_securitygroup",
    "networkacl": "query_networkacl",
    "peering": "query_peering",
    "rds": "query_rds",
    "dcs": "query_dcs",
    "dds": "query_dds",
    "dms": "query_dms",
    "gaussdb": "query_gaussdb",
    "geminidb": "query_geminidb",
    "taurusdb": "query_taurusdb",
    "live": "query_live",
    "nat": "query_nat",
    "vpn": "query_vpn",
    "vpcep": "query_vpcep",
    "dns": "query_dns",
    "er": "query_er",
    "waf": "query_waf",
    "cfw": "query_cfw",
    "cnad": "query_cnad",
    "cc2": "query_cc2",
    "workspace": "query_workspace",
    "dcaas": "query_dcaas",
    "bms":       "query_bms",
    "cci":       "query_cci",
    "sfs":       "query_sfs",
    "css":       "query_css",
    "mrs":       "query_mrs",
    "dli":       "query_dli",
    "cloudtable": "query_cloudtable",
    "bgp":       "query_bgp",
}
ALL_SERVICES = sorted(SERVICE_MODULES.keys())

# Account-level / global services: queried once per account (region tag = global)
GLOBAL_SERVICES = {"geip", "cdn", "ccaas", "eps", "cc2", "rms", "obs"}

# Region-restricted services: only the listed regions are queried (not iterated across all discovered regions under --regions auto)
# LIVE domains: RMS ListAllResources --type=live.domain has service endpoints in only 5 regions
SERVICE_REGION_WHITELIST = {
    "live": ["ap-southeast-3", "cn-north-1", "cn-east-3", "ap-southeast-2", "cn-north-4"],
}

# Default service-level concurrency
DEFAULT_WORKERS = 8


def parse_regions(args) -> list[str]:
    """Parse --region / --regions; default auto ([] = auto)."""
    explicit = args.regions or (args.region if args.region else "")
    if not explicit or explicit.strip().lower() == "auto":
        return []
    return [r.strip() for r in explicit.split(",") if r.strip()]


def run_service(module_name: str, hcloud, regions: list[str], out_root: Path,
                with_regions: bool = True, extra_kwargs: dict | None = None) -> dict:
    """Invoke a service script in isolation (local: run_regions per region; global: run once with label=global).

    A failure does not affect other services.
    """
    kwargs = dict(extra_kwargs or {})
    try:
        module = importlib.import_module(module_name)
        if with_regions:
            result = module.run_regions(hcloud, regions, out_root, **kwargs)
        else:
            result = {  # global service single execution
                "regions": {"global": module.run(hcloud, IAM_BASE_REGION, out_root, **kwargs)}}
        return result
    except Exception as exc:
        return {"error": str(exc)[:400]}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrate per-service resource queries across regions (KooCLI, concurrent)")
    parser.add_argument("--account", required=True, help="Account name (output directory name)")
    parser.add_argument("--region", default="", help="Single region (backward compatible, equivalent to --regions with one item)")
    parser.add_argument("--regions", default="",
                        help="Region list (comma-separated); default auto: discover all regions of the account and probe those with resources")
    parser.add_argument("--services", default=",".join(ALL_SERVICES),
                        help="Comma-separated service list (default all: " + ",".join(ALL_SERVICES) + ")")
    parser.add_argument("--workers", type=int, default=0,
                        help=f"Service-level concurrency threads (0=auto[{DEFAULT_WORKERS}], 1=serial fallback)")
    parser.add_argument("--region-workers", type=int, default=0,
                        help="Region-level concurrency threads (0=auto[5], 1=serial fallback; passed through to each service script)")
    parser.add_argument("--output-dir", default="", help="Output root directory (default ./resource-output/<account>)")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path (default auto-lookup)")
    args = parser.parse_args()

    hcloud = find_hcloud(args.hcloud_path)
    services = [s.strip().lower() for s in args.services.split(",") if s.strip()]
    unknown = [s for s in services if s not in SERVICE_MODULES]
    if unknown:
        log(f"Unknown services: {unknown} (available: {ALL_SERVICES})")
        return 1

    # -- preflight dependency self-check --
    # All third-party Python deps are checked in Step 1 (check_koocli.check_python_deps);
    # verify deps are ready before querying (fails loudly instead of silently skipping).
    log("preflight: checking Python dependencies ...")
    if not check_koocli.check_python_deps():
        log("Blocking dependency missing. Run Step 1 (check_koocli.py) or `pip install` it, then retry.")
        return 1

    out_root = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "resource-output" / args.account
    out_root.mkdir(parents=True, exist_ok=True)

    # -- Region list --
    regions = parse_regions(args)
    if not regions:
        log("Region auto mode: discovering account regions via IAM ...")
        regions = discover_regions(hcloud)
        if not regions:
            log("Region discovery failed; use --region/--regions to specify explicitly")
            return 1
        log(f"Discovered {len(regions)} regions: {regions}")
        active = []
        for r in regions:
            ok, why = probe_region(hcloud, r)
            log(f"  Probe {r}: {why} -> {'OK has resources' if ok else 'X skip'}")
            if ok:
                active.append(r)
        regions = active
    log(f"Regions to query: {regions}")
    if not regions:
        log("No regions with resources were found")
        return 0

    # -- Concurrency parameters --
    # Pass region-workers through to each service script via an env var (avoids modifying every run_regions signature)
    if args.region_workers:
        os.environ["HCLOUD_REGION_WORKERS"] = str(args.region_workers)

    local_services = [s for s in services if s not in GLOBAL_SERVICES]
    global_services = [s for s in services if s in GLOBAL_SERVICES]

    # Build task list: (service_name, is_global)
    tasks = [(svc, True) for svc in global_services] + [(svc, False) for svc in local_services]

    summary = {"account": args.account, "regions": regions, "services": {}}

    # -- Concurrent execution --
    workers = args.workers if args.workers > 0 else DEFAULT_WORKERS
    workers = min(workers, len(tasks))  # no more than the number of tasks

    if workers == 1:
        # Serial fallback (compatibility / debugging)
        log(f"Serial mode (workers=1), {len(tasks)} services total")
        for svc, is_global in tasks:
            if is_global:
                log(f"=== Global resource {svc} (once per account) ===")
                summary["services"][svc] = run_service(
                    SERVICE_MODULES[svc], hcloud, regions, out_root,
                    with_regions=False, extra_kwargs={"label": "global"})
            else:
                eff = SERVICE_REGION_WHITELIST.get(svc, regions)
                log(f"=== Service {svc} (regions {eff}) ===")
                summary["services"][svc] = run_service(
                    SERVICE_MODULES[svc], hcloud, eff, out_root)
    else:
        log(f"Concurrent mode: {workers} threads, {len(tasks)} services")
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="svc") as pool:
            future_map: dict = {}
            for svc, is_global in tasks:
                if is_global:
                    fut = pool.submit(run_service, SERVICE_MODULES[svc], hcloud, regions,
                                      out_root, with_regions=False,
                                      extra_kwargs={"label": "global"})
                else:
                    eff = SERVICE_REGION_WHITELIST.get(svc, regions)
                    fut = pool.submit(run_service, SERVICE_MODULES[svc], hcloud, eff,
                                      out_root)
                future_map[fut] = (svc, is_global)

            for future in as_completed(future_map):
                svc, is_global = future_map[future]
                tag = "global" if is_global else "region"
                try:
                    result = future.result()
                    summary["services"][svc] = result
                    # Extract count summary
                    if "error" in result:
                        log(f"  X [{tag}] {svc} failed: {result['error']}")
                    else:
                        log(f"  V [{tag}] {svc} completed")
                except Exception as exc:
                    summary["services"][svc] = {"error": str(exc)[:400]}
                    log(f"  X [{tag}] {svc} exception: {exc}")

    # Summary report
    report_path = out_root / f"query_report_{timestamp()}.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Query complete; report: {report_path}")

    # -- Failure feedback --
    # A query run must NOT report success when services failed. Count per-service errors:
    # auth failures abort the pipeline (rc=2); any other service error is surfaced (rc=1)
    # so the caller (run_pipeline Step 2) can stop instead of producing an empty marker table.
    failed = [svc for svc, res in summary["services"].items() if isinstance(res, dict) and "error" in res]
    if failed:
        auth_failed = [svc for svc in failed
                       if is_auth_error(str(summary["services"][svc].get("error", "")))]
        if auth_failed:
            log(f"Authentication failure for services: {auth_failed}. "
                "Check AK/SK configuration or IAM permissions before retrying.")
            return 2
        log(f"{len(failed)} service(s) failed: {failed}. Inspect query_report for details.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
