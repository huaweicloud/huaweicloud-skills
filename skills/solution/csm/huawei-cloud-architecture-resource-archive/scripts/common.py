#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common module for KooCLI queries: hcloud lookup/execution, JSON stripping, counting, region discovery/probing, concurrent query.

Shared by all query_<service>.py standalone scripts to avoid code duplication.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marker_constants import HCLOUD_MULTI_VERSION_PROMPT_HINT

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INSTALL_DIR = SCRIPT_DIR.parent / "koocli"
IAM_BASE_REGION = "cn-north-4"  # IAM KeystoneListProjects is an account-level API; any available region works

# Thread-safe log lock
_log_lock = threading.Lock()


def log(msg: str) -> None:
    with _log_lock:
        print(f"[query] {msg}")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_hcloud(custom: str = "") -> Path:
    exe = "hcloud.exe" if os.name == "nt" else "hcloud"
    if custom:
        p = Path(custom)
        if p.is_dir():
            p = p / exe
        if p.exists():
            return p
    found = shutil.which(exe)
    if found:
        return Path(found)
    cand = DEFAULT_INSTALL_DIR / exe
    if cand.exists():
        return cand
    raise RuntimeError(
        "KooCLI (hcloud) not found. Run scripts/check_koocli.py first to install and configure it, "
        "or pass its location via --hcloud-path."
    )


def strip_non_json(raw: str) -> str:
    """Remove ANSI color codes and the KooCLI multi-version prompt line (HCLOUD_MULTI_VERSION_PROMPT_HINT), keeping only the JSON part."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    p1 = clean.find("{")
    p2 = clean.find("[")
    pos = p1 if p1 >= 0 and (p2 < 0 or p1 < p2) else p2
    return clean[pos:] if pos >= 0 else ""


def run_hcloud(hcloud: Path, cli_service: str, operation: str, region: str,
               extra_args: list[str] | None = None) -> str:
    """Execute an hcloud command and return its stdout **after stripping prompt lines**; raises on failure."""
    cmd = [str(hcloud), cli_service, operation, f"--cli-region={region}"]
    if extra_args:
        cmd.extend(extra_args)
    # Some APIs (CCE ListClusters) require Content-Type; MRS ListClusters rejects it
    if cli_service == "CCE" and operation in ("ListClusters",):
        cmd.append('--Content-Type="application/json"')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(f"hcloud {cli_service} {operation} failed: {out[:400]}")
    # KooCLI reports auth/config errors in stdout with exit code 0 (USE_ERROR / OPENAPI_ERROR).
    # Detect them so a query run cannot silently "succeed" with zero rows.
    if is_auth_error(out):
        raise RuntimeError(f"hcloud {cli_service} {operation} authentication error: {strip_non_json(out)[:400]}")
    body = strip_non_json(out)  # error Status may be on stderr
    if not body:
        raise RuntimeError(f"hcloud {cli_service} {operation} produced no JSON output: {out[:300]}")
    return body


_AUTH_ERROR_MARKERS = ("APIGW.0301", "Unauthorized", "Incorrect IAM authentication",
                       "认证信息不正确", "AK/SK not found")


def is_auth_error(out: str) -> bool:
    """True when KooCLI output indicates an authentication failure.

    Only IAM-level auth markers are matched (APIGW.0301 / Unauthorized / AK-SK missing);
    per-service usage errors (USE_ERROR/OPENAPI_ERROR) are NOT treated as auth failures
    because they may be legitimate "resource absent" responses.
    """
    stripped = out.strip()
    if not stripped:
        return False
    return any(marker in stripped for marker in _AUTH_ERROR_MARKERS)


def get_project_id(hcloud: Path, region: str = "cn-north-4") -> str:
    """Resolve the account project_id for a region via IAM KeystoneListProjects.

    Some KooCLI operations (e.g. CCE ListClusters) fail to auto-resolve project_id
    under a corporate proxy; passing it explicitly avoids that path.
    """
    try:
        raw = run_hcloud(hcloud, "IAM", "KeystoneListProjects", region)
        data = parse_body(raw)
        for p in (data.get("projects") or []) if isinstance(data, dict) else []:
            if str(p.get("name")) == region and p.get("id"):
                return str(p.get("id"))
    except (RuntimeError, json.JSONDecodeError, AttributeError):
        pass
    return ""


def parse_body(raw: str):
    """Strip prompt lines / trailing noise and parse JSON; returns None on failure (reused by query counters and converters)."""
    body = strip_non_json(raw)
    if not body:
        return None
    p1 = body.find("{")
    p2 = body.find("[")
    start = p1 if p1 >= 0 and (p2 < 0 or p1 < p2) else p2
    end = max(body.rfind("}"), body.rfind("]"))
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(body[start:end + 1])
    except json.JSONDecodeError:
        return None


def count_items(data, keys: tuple[str, ...] = ("items", "resources", "vpcs", "buckets",
                                                 "servers", "domains", "global_eips",
                                                 "cloud_connections", "clusters",
                                                 "providers", "loadbalancers", "pools",
                                                 "members", "enterprise_projects",
                                                 "subnets", "routetables",
                                                 "security_groups", "firewalls",
                                                 "vpc_peerings", "peerings", "publicips",
                                                 "inter_region_bandwidths",
                                                 "bandwidth_packages",
                                                 "network_instances",
                                                 "domain_info",
                                                 "nat_gateways", "snat_rules", "dnat_rules",
                                                 "vpn_gateways", "vpn_connections",
                                                 "customer_gateways", "p2c_vpn_gateways",
                                                 "endpoints", "zones", "resolver_rules",
                                                 "instances", "route_tables",
                                                 "attachments", "shares",
                                                 "queues", "jobs", "databases",
                                                 "datasource_connections",
                                                 "desktops")) -> int:
    """Count resource entries from a parsed JSON."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in keys:
            if isinstance(data.get(key), list):
                return len(data[key])
    return 0


# ═══════════════════ Concurrent region query ═══════════════════

def run_regions_concurrent(run_fn, hcloud, regions: list[str], out_root,
                           max_workers: int = 0, **kwargs) -> dict:
    """Run each region's query function concurrently, returning {region: result}.

    Essentially a concurrent replacement for the ``for region in regions: run(...)`` serial loop
    in each service script. Different regions write to different files (filenames include the region),
    so there is no contention.

    Parameters:
        run_fn:   the run(hcloud, region, out_root, **kwargs) function for each service
        hcloud:   hcloud executable path
        regions:  list of regions
        out_root: output root directory
        max_workers: concurrency thread count; 0=auto(min(len(regions), 5)), 1=serial fallback
        **kwargs: additional parameters passed through to run_fn (e.g. label, with_k8s)

    Returns:
        {region: run_fn return value} dict, with the same interface as the serial version
    """
    if not regions:
        return {}

    # Single region or explicit serial → call directly to avoid thread pool overhead
    if len(regions) == 1 or max_workers == 1:
        return {r: run_fn(hcloud, r, out_root, **kwargs) for r in regions}

    # Auto-select thread count: at most 5 concurrent regions (avoid API throttling)
    workers = min(len(regions), max_workers) if max_workers > 1 else min(len(regions), 5)

    results: dict = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="region") as pool:
        future_map = {pool.submit(run_fn, hcloud, r, out_root, **kwargs): r for r in regions}
        for future in as_completed(future_map):
            region = future_map[future]
            try:
                results[region] = future.result()
            except Exception as exc:
                results[region] = {"error": str(exc)[:400]}
                log(f"  [{region}] region query failed: {exc}")
    return results


# ═══════════════════ Region discovery / probing ═══════════════════

def discover_regions(hcloud: Path) -> list[str]:
    """IAM KeystoneListProjects → regions enabled for the account (project name is the region name)."""
    try:
        body = run_hcloud(hcloud, "IAM", "KeystoneListProjects", IAM_BASE_REGION)
        data = json.loads(body)
        regions = []
        for p in data.get("projects") or []:
            if p.get("is_domain"):
                continue
            name = (p.get("name") or "").strip()
            if name and p.get("enabled", True) and name not in regions:
                regions.append(name)
        return regions
    except Exception as exc:
        log(f"Region discovery failed (IAM KeystoneListProjects): {exc}")
        return []


def probe_region(hcloud: Path, region: str,
                 service_specs: dict | None = None) -> tuple[bool, str]:
    """Decide whether a region should be queried (avoid using a single service as a proxy that causes missed regions).

    - Regions supported by RMS CollectAllResourcesSummary: authoritative (aggregates all resource types;
      a type count of 0 → skip to avoid empty runs)
    - Regions not supported by RMS: **do not skip, treat as having resources** (return True for full query),
      because judging only by VPC/ECS would miss regions that have only OBS/DNS resources;
      the actual returned count is given by each query script, and the marker table only includes resources that actually exist.
    Returns (should_query, basis).
    """
    del service_specs  # parameter kept for backward compatibility
    try:
        body = run_hcloud(hcloud, "RMS", "CollectAllResourcesSummary", region)
        data = json.loads(body)
        n = count_items(data)
        if n > 0:
            return True, f"RMS({n} resource types)"
        return False, "RMS(0 resource types)"
    except (RuntimeError, json.JSONDecodeError):
        # RMS does not support this region (verified: only cn-north-4 supports it) → cannot decide based on it, conservatively do a full query
        return True, "RMS not supported → full query"
