#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query CCI cloud container instances (standalone script with full-region query capability).

CCI is k8s-style API (no ListInstances); namespaces act as the primary resource.
Optional: listNamespacedPods per namespace for pod-level detail.

Usage:
    python query_cci.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]
Output: <output-dir>/CCI/temp/CCI_instances_<region>_<ts>.json
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, run_regions_concurrent)  # noqa: E402

SERVICE_DIR = "CCI"


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    """Query CCI namespaces + pods (k8s-style API).

    Namespaces are the organizational unit; pods carry the actual workloads
    (container resources with CPU/memory limits) that map onto the spec column.
    """
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "cci", "files": []}
    total = 0

    # 1. Namespaces (organizational unit)
    try:
        raw = run_hcloud(hcloud, "CCI", "listNamespaces", region)
        path = svc_dir / f"CCI_namespaces_{tag}_{ts}.json"
        path.write_text(raw, encoding="utf-8")
        result["files"].append(str(path))
        count = count_items(parse_body(raw))
        total += count
        log(f"[CCI] saved {path} ({count} namespaces)")
    except RuntimeError as exc:
        log(f"[CCI] listNamespaces failed: {exc}")

    # 2. Pods (per namespace, carry container resources for spec extraction)
    # listCoreV1PodForAllNamespaces returns items:null on this account, so iterate
    # namespaces explicitly and call listNamespacedPods per namespace.
    try:
        ns_raw = run_hcloud(hcloud, "CCI", "listNamespaces", region)
        ns_data = parse_body(ns_raw)
        ns_names = [str(n.get("metadata", {}).get("name"))
                    for n in (ns_data.get("items") or []) if n.get("metadata", {}).get("name")]
        all_pods = []
        for ns in ns_names:
            try:
                p_raw = run_hcloud(hcloud, "CCI", "listNamespacedPods", region,
                                   ["--namespace=" + ns])
                p_data = parse_body(p_raw) or {}
                all_pods.extend(p_data.get("items") or [])
            except RuntimeError as exc:
                log(f"[CCI] listNamespacedPods for {ns} failed: {exc}")
        merged = {"kind": "PodList", "apiVersion": "cci/v2", "metadata": {}, "items": all_pods}
        merged_raw = json.dumps(merged, ensure_ascii=False)
        path = svc_dir / f"CCI_pods_{tag}_{ts}.json"
        path.write_text(merged_raw, encoding="utf-8")
        result["files"].append(str(path))
        total += len(all_pods)
        log(f"[CCI] saved {path} ({len(all_pods)} pods)")
    except RuntimeError as exc:
        log(f"[CCI] pods query failed: {exc}")

    result["count"] = total
    return result


def run_regions(hcloud, regions, out_root, label=None):
    return {"service": "cci", "regions": run_regions_concurrent(run, hcloud, regions, out_root, label=label)}


def resolve_regions(hcloud, args):
    explicit = args.regions or (args.region or "")
    if not explicit or explicit.strip().lower() == "auto":
        regions = discover_regions(hcloud)
        if not regions:
            return []
        return [r for r in regions if probe_region(hcloud, r)[0]]
    return [r.strip() for r in explicit.split(",") if r.strip()]


def main():
    parser = argparse.ArgumentParser(description="Query CCI cloud container instances via KooCLI")
    parser.add_argument("--region", default="")
    parser.add_argument("--regions", default="auto")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--hcloud-path", default="")
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
