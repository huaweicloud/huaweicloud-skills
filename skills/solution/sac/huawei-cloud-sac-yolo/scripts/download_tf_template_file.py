#!/usr/bin/env python
"""Download a Terraform template file (.tf or .tf.json) to local directory."""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Terraform template file from URL.")
    parser.add_argument("--url", required=True, help="Template URL (expected .tf or .tf.json)")
    parser.add_argument("--out-dir", required=True, help="Output directory (Terraform working directory)")
    parser.add_argument("--filename", default="", help="Optional target filename")
    parser.add_argument("--timeout", type=int, default=120, help="Download timeout in seconds")
    return parser.parse_args()


def guess_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name.strip()
    if not name:
        return "main.tf"
    return name


def ensure_tf_name(name: str, url: str) -> str:
    if name.lower().endswith(".tf") or name.lower().endswith(".tf.json"):
        return name
    # Keep strict behavior to avoid silently saving non-template assets.
    raise RuntimeError(f"URL does not look like a Terraform template file: {url}")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    target_name = args.filename.strip() or guess_filename(args.url)
    target_name = ensure_tf_name(target_name, args.url)
    target = out_dir / target_name

    req = urllib.request.Request(
        args.url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; find-and-deploy-sac/1.0)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp, target.open("wb") as f:
            shutil.copyfileobj(resp, f)
    except Exception as exc:  # noqa: BLE001
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(f"Downloaded template: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
