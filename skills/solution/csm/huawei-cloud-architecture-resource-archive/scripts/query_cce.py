#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query CCE resources (standalone script: clusters + per-cluster nodes + K8s sub-resources, independent of other services).

Flow:
  1. CCE ListClusters → CCE/temp/CCE_cce_cluster_vm_new_<region>_<ts>.json
  2. ListNodes per cluster → CCE/temp/CCE_vm_nodes_new_<cluster-name>_<uid>_<region>_<ts>.json
  3. Optional (default on): call query_cce_k8s.py to query K8s sub-resources (Deployment/Service/ConfigMap etc.,
     requires pip install kubernetes; clusters without a usable endpoint are skipped automatically)

Usage:
    python query_cce.py --regions auto --output-dir <raw output dir> [--no-k8s] [--hcloud-path <hcloud>]

Full-region (default auto): IAM discovers regions → RMS/VPC/ECS probe → query clusters+nodes+K8s per region.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body, timestamp, log,
                    run_regions_concurrent, get_project_id)  # noqa: E402

SERVICE_DIR = "CCE"
SERVICE_SPEC = {"cli_service": "CCE", "operation": "ListClusters",
                "tsc_interface": "cce_cluster_vm_new"}


def run(hcloud: Path, region: str, out_root: Path, with_k8s: bool = True) -> dict:
    """Query CCE clusters + nodes (+ K8s sub-resources) for one region."""
    spec = SERVICE_SPEC
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "cce", "tsc_interface": spec["tsc_interface"], "files": []}

    # CCE ListClusters needs an explicit project_id (auto-resolution fails under corporate proxy)
    pid = get_project_id(hcloud, region)
    extra = ["--project_id=" + pid] if pid else []
    raw = run_hcloud(hcloud, spec["cli_service"], spec["operation"], region, extra)
    path = svc_dir / f"{SERVICE_DIR}_{spec['tsc_interface']}_{region}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    result["files"].append(str(path))
    try:
        count = count_items(parse_body(raw))
    except json.JSONDecodeError:
        count = 0
    result["count"] = count
    log(f"[CCE] saved {path} ({count} rows)")

    # List nodes per cluster (ListNodes)
    try:
        data = json.loads(raw)
        clusters = data.get("items") or []
        for c in clusters:
            cid = (c.get("metadata") or {}).get("uid") or c.get("id")
            if not cid:
                continue
            try:
                nodes_raw = run_hcloud(hcloud, "CCE", "ListNodes", region,
                                       ["--cluster_id=" + cid])
                npath = svc_dir / f"CCE_vm_nodes_new_{c.get('metadata',{}).get('name',cid)}_{cid}_{region}_{ts}.json"
                npath.write_text(nodes_raw, encoding="utf-8")
                result["files"].append(str(npath))
                log(f"  [CCE] cluster {cid} nodes saved")
            except RuntimeError as exc:
                log(f"  [CCE] cluster {cid} nodes query failed: {exc}")
    except json.JSONDecodeError:
        pass

    # K8s sub-resources (optional)
    if with_k8s:
        try:
            import query_cce_k8s
            k8s_result = query_cce_k8s.run(hcloud, region, out_root)
            result["files"].extend(k8s_result.get("files", []))
        except Exception as exc:
            log(f"  [CCE] K8s sub-resource query skipped: {exc}")

    return result


def run_regions(hcloud, regions: list[str], out_root: Path, with_k8s: bool = True) -> dict:
    """Query CCE per region (full-region merging is done by the dispatcher/convert)."""
    results = run_regions_concurrent(run, hcloud, regions, out_root, with_k8s=with_k8s)

    return {"service": "cce", "regions": results}


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
    parser = argparse.ArgumentParser(description="Query CCE clusters/nodes/k8s via KooCLI (multi-region)")
    parser.add_argument("--region", default="", help="Single region (shorthand for --regions)")
    parser.add_argument("--regions", default="auto", help="Region list (comma-separated) or auto (default: auto-discover + probe)")
    parser.add_argument("--output-dir", required=True, help="KooCLI raw output directory")
    parser.add_argument("--no-k8s", action="store_true", help="Skip K8s sub-resource queries")
    parser.add_argument("--hcloud-path", default="", help="hcloud executable/directory path")
    args = parser.parse_args()
    hcloud = find_hcloud(args.hcloud_path)
    regions = resolve_regions(hcloud, args)
    if not regions:
        return 1
    result = run_regions(hcloud, regions, Path(args.output_dir), with_k8s=not args.no_k8s)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())