#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query CSS Cloud Search Service clusters (standalone script with full-region query capability).

Usage:
    python query_css.py --regions auto --output-dir <raw output dir> [--hcloud-path <hcloud>]
Output: <output-dir>/CSS/temp/CSS_clusters_<region>_<ts>.json
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (find_hcloud, run_hcloud, count_items, parse_body,
                    timestamp, log, discover_regions, probe_region, run_regions_concurrent)  # noqa: E402

SERVICE_DIR = "CSS"


def run(hcloud: Path, region: str, out_root: Path, label: str | None = None) -> dict:
    tag = label or region
    svc_dir = out_root / SERVICE_DIR / "temp"
    svc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    # CSS uses ListClustersDetails (ListClusters is not a valid operation)
    raw = run_hcloud(hcloud, "CSS", "ListClustersDetails", region)
    path = svc_dir / f"CSS_clusters_{tag}_{ts}.json"
    path.write_text(raw, encoding="utf-8")
    count = count_items(parse_body(raw))
    log(f"[CSS] saved {path} ({count} rows)")
    return {"service": "css", "files": [str(path)], "count": count}


def run_regions(hcloud, regions, out_root, label=None):
    return {"service": "css", "regions": run_regions_concurrent(run, hcloud, regions, out_root, label=label)}


def resolve_regions(hcloud, args):
    explicit = args.regions or (args.region or "")
    if not explicit or explicit.strip().lower() == "auto":
        regions = discover_regions(hcloud)
        if not regions:
            return []
        return [r for r in regions if probe_region(hcloud, r)[0]]
    return [r.strip() for r in explicit.split(",") if r.strip()]


def main():
    parser = argparse.ArgumentParser(description="Query CSS clusters via KooCLI")
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
