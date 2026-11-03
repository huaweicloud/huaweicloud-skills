#!/usr/bin/env python3
"""Check the ocms environment and verify OcmsRecorder end to end.

Runs in the active Python environment and needs no arguments, so the same
command works on the Octopus platform, on a developer machine, and in an
evaluation environment where the proprietary ``ocms`` package cannot be
installed.

Usage
-----
    python3 scripts/verify_ocms.py
        Self-test: log a few synthetic steps into a temporary directory.
        * ocms installed     -> metrics.json and the chart CSVs must be produced
        * ocms not installed -> the recorder must degrade gracefully
                                (disable itself, no exception, no files)

    python3 scripts/verify_ocms.py --output-dir "$OUTPUT_DIR"
        Check the metric files of a real training run. The metric directory
        is ``$METRICS`` when set (Octopus platform), else
        ``<output_dir>/ocms_metrics``. An empty value falls back to the
        self-test.

    python3 scripts/verify_ocms.py --require-ocms
        Same as the self-test, but fail when ocms is not installed (use on
        the Octopus platform, where metric reporting is expected).

Exit codes: 0 = verified (including the graceful-degradation path), 1 = failed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocms_recorder import OcmsRecorder  # noqa: E402

SAMPLE_STEPS = [
    (1, {"loss": 1.20, "learning_rate": 1e-4, "timing/data": 0.05, "timing/model": 0.30, "grad_norm": 2.1, "epoch": 0}),
    (2, {"loss": 0.95, "learning_rate": 1e-4, "timing/data": 0.04, "timing/model": 0.29, "grad_norm": 1.8, "epoch": 0}),
    (3, {"loss": 0.80, "learning_rate": 9e-5, "timing/data": 0.04, "timing/model": 0.28, "grad_norm": 1.5, "epoch": 1}),
]
EXPECTED_CHARTS = ["loss", "learning_rate", "epoch", "timing", "grad_norm"]


def ocms_status() -> tuple[bool, str]:
    if importlib.util.find_spec("ocms") is None:
        return False, "not installed"
    try:
        from importlib.metadata import version
        return True, version("ocms")
    except Exception:  # noqa: BLE001 - version metadata is optional
        return True, "unknown version"


def check_metric_dir(metrics_dir: str, expected_charts: list[str] | None = None, min_rows: int = 1) -> list[str]:
    """Return a list of problems found in an ocms metric directory."""
    problems = []
    meta_path = os.path.join(metrics_dir, "metrics.json")
    if not os.path.isfile(meta_path):
        return [f"missing {meta_path}"]
    try:
        with open(meta_path, encoding="utf-8") as f:
            json.load(f)
    except (OSError, ValueError) as exc:
        problems.append(f"metrics.json is not valid JSON: {exc}")
    csvs = sorted(n for n in os.listdir(metrics_dir) if n.endswith(".csv"))
    if not csvs:
        problems.append(f"no chart CSV files in {metrics_dir}")
    for chart in expected_charts or []:
        if f"{chart}.csv" not in csvs:
            problems.append(f"missing chart file {chart}.csv")
    for name in csvs:
        with open(os.path.join(metrics_dir, name), encoding="utf-8") as f:
            rows = [line for line in f if line.strip()]
        if len(rows) < min_rows:
            problems.append(f"{name} has {len(rows)} rows, expected >= {min_rows}")
    return problems


def self_test(require_ocms: bool) -> int:
    installed, ver = ocms_status()
    print(f"ocms: {'installed (' + ver + ')' if installed else 'not installed'}")
    if require_ocms and not installed:
        print("FAIL: --require-ocms was given but the ocms package is not installed")
        return 1
    with tempfile.TemporaryDirectory(prefix="ocms_verify_") as tmp:
        recorder = OcmsRecorder(log_dir=tmp)
        try:
            for step, metrics in SAMPLE_STEPS:
                recorder.log(step=step, metrics=metrics)
            recorder.finish()
        except Exception as exc:  # noqa: BLE001 - recorder must never raise
            print(f"FAIL: recorder raised {type(exc).__name__}: {exc}")
            return 1
        if not installed:
            if recorder.enabled or os.listdir(tmp):
                print("FAIL: ocms is missing but the recorder did not disable itself cleanly")
                return 1
            print("OK: graceful degradation verified (recorder disabled itself, training is unaffected)")
            print("    Install ocms on the Octopus platform to enable metric reporting.")
            return 0
        problems = [] if recorder.enabled else ["recorder disabled itself although ocms is installed"]
        problems += check_metric_dir(tmp, EXPECTED_CHARTS, min_rows=len(SAMPLE_STEPS))
        if problems:
            print("FAIL:\n  " + "\n  ".join(problems))
            return 1
        print(f"OK: metrics.json and {len(EXPECTED_CHARTS)} chart CSVs produced with {len(SAMPLE_STEPS)} rows each")
        return 0


def check_output_dir(output_dir: str) -> int:
    metrics_dir = os.getenv("METRICS") or os.path.join(output_dir, "ocms_metrics")
    installed, ver = ocms_status()
    print(f"ocms: {'installed (' + ver + ')' if installed else 'not installed'}")
    print(f"metric dir: {metrics_dir}")
    if not installed:
        print("OK: ocms is not installed, so no metric files are expected (graceful-degradation path)")
        return 0
    if not os.path.isdir(metrics_dir):
        print(f"FAIL: metric directory not found: {metrics_dir} (run a short training first)")
        return 1
    problems = check_metric_dir(metrics_dir)
    if problems:
        print("FAIL:\n  " + "\n  ".join(problems))
        return 1
    csvs = sorted(n for n in os.listdir(metrics_dir) if n.endswith(".csv"))
    print(f"OK: metrics.json + {len(csvs)} chart CSVs: {', '.join(csvs)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output-dir", default="", help="training output dir to check (empty = self-test)")
    parser.add_argument("--require-ocms", action="store_true", help="fail when ocms is not installed")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="  [recorder] %(message)s")
    if args.output_dir.strip():
        return check_output_dir(args.output_dir.strip())
    return self_test(args.require_ocms)


if __name__ == "__main__":
    sys.exit(main())
