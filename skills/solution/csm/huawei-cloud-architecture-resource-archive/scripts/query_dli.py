#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query DLI Data Lake Insight resources and their sub-types (regional, standalone script with full-region query).

4 DLI resource types are required:
  - DLI_Queue       → DLI ListQueues                  (list_key: queues)
  - DLI_FlinkJob    → DLI ListFlinkJobs               (list_key: jobs)
  - DLI_Database    → DLI ListDatabases               (list_key: databases)
  - DLI_CrossSource → DLI ListDatasourceConnections   (list_key: datasource_connections)

Usage:
    python query_dli.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, run_regions_concurrent)  # noqa: E402

SERVICE_DIR = "DLI"

# 4 sub-resource types: (tsc_interface, operation, list_key)
DLI_SUB_RESOURCES = [
    ("queues",                 "ListQueues",                  "queues"),
    ("flink_jobs",             "ListFlinkJobs",               "job_list"),
    ("databases",              "ListDatabases",               "databases"),
    ("datasource_connections", "ListDatasourceConnections",   "connections"),
]


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    result: dict = {"service": "dli", "files": []}
    total = 0

    for tsc_iface, operation, _key in DLI_SUB_RESOURCES:
        try:
            raw = run_hcloud(hcloud, "DLI", operation, region)
            path = svc_dir / f"DLI_{tsc_iface}_{tag}_{ts}.json"
            path.write_text(raw, encoding="utf-8")
            result["files"].append(str(path))
            count = count_items(parse_body(raw))
            total += count
            log(f"[DLI] {tsc_iface} saved {path} ({count} rows)")
        except RuntimeError as exc:
            log(f"[DLI] {operation} query failed: {exc}")

    result["count"] = total
    return result


def run_regions(hcloud, regions, out_root, label=None):
    return {"service": "dli", "regions": run_regions_concurrent(run, hcloud, regions, out_root, label=label)}


def resolve_regions(hcloud, args):
    explicit = args.regions or (args.region or "")
    if not explicit or explicit.strip().lower() == "auto":
        regions = discover_regions(hcloud)
        if not regions:
            return []
        return [r for r in regions if probe_region(hcloud, r)[0]]
    return [r.strip() for r in explicit.split(",") if r.strip()]


def main():
    parser = argparse.ArgumentParser(description="Query DLI queues/jobs/databases/connections via KooCLI")
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
