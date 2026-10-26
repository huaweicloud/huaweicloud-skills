#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-click full pipeline: environment check → full query → format conversion → marker table generation.

Chains the 4 scripts that previously had to be run manually in order into a single command;
any step failure aborts and reports an error. The agent only needs to run this script to
complete the full flow without skipping prerequisite dependency checks.

Steps:
  1. check_koocli.py           — check/install KooCLI + AK/SK config + kubernetes client
  2. query_resources.py        — full-region full-service resource query (KooCLI concurrent), outputs raw JSON
  3. convert_to_tsc_json.py    — convert to marker-table store compatible JSON; deletes raw JSON after conversion
  4. generate_marker_table.py  — generate 关键资源标记表.xlsx + store JSON

Output directory convention:
  resource-output/
  └── <account>-<timestamp>/
      ├── converted/           ← Step 3 output (converted JSON)
      └── marker/              ← Step 4 output (关键资源标记表.xlsx + _resource_store.json)

  The raw query JSON from Step 2 is automatically deleted after Step 3 conversion completes.

Usage:
    python run_pipeline.py --account <account-name> [options]

    Common:
      python run_pipeline.py --account hcloud-account
      python run_pipeline.py --account hcloud-account --regions cn-north-4,cn-east-3
      python run_pipeline.py --account hcloud-account --services cce,vpc,ecs

Options:
    --account         account name (output directory name, required)
    --regions         comma-separated region list; default auto discovery
    --region          single region (backward compatible)
    --services        comma-separated service list (default: all)
    --workers         service-level concurrency threads (0=auto[8])
    --region-workers  region-level concurrency threads (0=auto[5])
    --output-dir      output root directory (default ./resource-output)
    --hcloud-path     hcloud path (default auto-lookup)
    --skip-query      skip Step 2 query (reuse existing converted results, only re-run marker table)
    --no-infer        pass to convert: skip downstream inference
    --no-clean        pass to convert: do not clean old outputs
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from marker_constants import MARKER_TABLE_FILENAME, RESOURCE_STORE_FILENAME

DEFAULT_OUTPUT_ROOT = SCRIPT_DIR.parent / "resource-output"


def log(msg: str) -> None:
    print(f"[pipeline] {msg}")


def run_step(step: int, name: str, cmd: list[str]) -> int:
    """Run one step, streaming stdout/stderr in real time, and return the exit code."""
    log(f"=== Step {step}/4: {name} ===")
    log(f"  Command: {' '.join(cmd)}")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    elapsed = time.time() - t0
    if result.returncode != 0:
        log(f"  X Step {step} failed (exit={result.returncode}, {elapsed:.1f}s)")
        return result.returncode
    log(f"  V Step {step} completed ({elapsed:.1f}s)")
    return 0


def find_latest_run(out_root: Path, account: str) -> Path | None:
    """Find the latest run directory for the given account."""
    if not out_root.exists():
        return None
    candidates = sorted(
        [d for d in out_root.iterdir()
         if d.is_dir() and d.name.startswith(f"{account}-")],
        key=lambda d: d.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-click full pipeline: environment check -> full query -> format conversion -> marker table generation",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--account", required=True, help="Account name (output directory name)")
    parser.add_argument("--region", default="", help="Single region (backward compatible)")
    parser.add_argument("--regions", default="", help="Region list (comma-separated); default auto")
    parser.add_argument("--services", default="", help="Comma-separated service list (default: all)")
    parser.add_argument("--workers", type=int, default=0, help="Service-level concurrency threads (0=auto[8])")
    parser.add_argument("--region-workers", type=int, default=0, help="Region-level concurrency threads (0=auto[5])")
    parser.add_argument("--output-dir", default="", help="Output root directory (default ./resource-output)")
    parser.add_argument("--hcloud-path", default="", help="hcloud path (default auto-lookup)")
    parser.add_argument("--skip-query", action="store_true", help="Skip Step 2 query (reuse existing converted results, re-run marker table only)")
    parser.add_argument("--no-infer", action="store_true", help="Pass through to convert: skip downstream inference")
    parser.add_argument("--no-clean", action="store_true", help="Pass through to convert: do not clean old outputs")
    args = parser.parse_args()

    py = sys.executable
    out_root = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT

    t_start = time.time()

    # -- Determine run directory --
    if args.skip_query:
        # Reuse existing results: find the latest run directory
        run_dir = find_latest_run(out_root, args.account)
        if run_dir is None:
            log(f"No existing run directory for account {args.account}; cannot --skip-query")
            return 1
        log(f"Reusing existing run directory: {run_dir}")
    else:
        # Create a new run directory with a timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_dir = out_root / f"{args.account}-{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

    raw_dir = run_dir / "raw"
    converted_dir = run_dir / "converted"
    marker_dir = run_dir / "marker"

    # -- Step 1: environment check --
    cmd = [py, "check_koocli.py"]
    rc = run_step(1, "Environment check + dependency install", cmd)
    if rc != 0:
        log("Environment check failed, aborting. Fix it and retry.")
        return rc

    # -- Step 2: full query --
    if not args.skip_query:
        cmd = [py, "query_resources.py", "--account", args.account,
               "--output-dir", str(raw_dir)]
        if args.region:
            cmd += ["--region", args.region]
        if args.regions:
            cmd += ["--regions", args.regions]
        if args.services:
            cmd += ["--services", args.services]
        if args.workers:
            cmd += ["--workers", str(args.workers)]
        if args.region_workers:
            cmd += ["--region-workers", str(args.region_workers)]
        if args.hcloud_path:
            cmd += ["--hcloud-path", args.hcloud_path]
        rc = run_step(2, "Full resource query", cmd)
        if rc != 0:
            log("Resource query failed, aborting")
            return rc
    else:
        log("Step 2/4: full query (skipped, reusing existing results)")

    # -- Step 3: format conversion --
    if not args.skip_query:
        cmd = [py, "convert_to_tsc_json.py",
               "--query-dir", str(raw_dir),
               "--customer", args.account,
               "--output", str(converted_dir)]
        if args.no_infer:
            cmd.append("--no-infer")
        if args.no_clean:
            cmd.append("--no-clean")
        rc = run_step(3, "Format conversion", cmd)
        if rc != 0:
            log("Format conversion failed, aborting")
            return rc

        # Delete raw JSON after conversion
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
            log(f"  Cleaned up raw query JSON: {raw_dir}")
    else:
        log("Step 3/4: format conversion (skipped, reusing existing results)")

    # -- Step 4: marker table generation --
    cmd = [py, "generate_marker_table.py",
           "--tsc-dir", str(converted_dir),
           "--out", str(marker_dir),
           "--customer", args.account]
    rc = run_step(4, "Marker table generation", cmd)
    if rc != 0:
        log("Marker table generation failed")
        return rc

    # -- Summary --
    elapsed = time.time() - t_start
    log(f"=== Full pipeline completed ({elapsed:.1f}s) ===")
    log(f"  Run directory: {run_dir}")
    log(f"  Converted:     {converted_dir}")
    log(f"  Marker table:  {marker_dir / MARKER_TABLE_FILENAME}")
    log(f"  Store:         {marker_dir / RESOURCE_STORE_FILENAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
