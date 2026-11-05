#!/usr/bin/env python3
"""Bottleneck diagnoser for Ascend NPU operators.

Reads Ascend profiling CSV output (e.g. OpBasicInfo.csv from msprof) and
auto-classifies each operator's performance bottleneck into one (or more) of:

  - memory-bound          : achieved memory bandwidth close to hardware peak
  - compute-bound         : compute units (AI Core) are the limiting resource
  - communication-bound   : collective/communication operator dominates runtime
  - operator-fallback     : operator ran on AI CPU / CPU (no AI Core kernel)

It further recommends concrete optimization measures with a priority rank
(P0/P1/P2) so agents and users can act on the most impactful items first.

Usage:
    python3 bottleneck_diagnoser.py --csv OpBasicInfo.csv \
        [--peak-tflops 294.91] [--peak-memory-bw 1200] [--threshold-bw 0.6]

Dependencies: Python 3.8+ standard library only (csv module).
"""

import argparse
import csv
import re
import sys
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Column name normalization
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    """Normalize a CSV header so we can match it regardless of spaces/case."""
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


def _find_col(headers: List[str], *candidates: str) -> Optional[int]:
    """Find the first header matching one of the candidate normalized names."""
    norm_headers = [_norm(h) for h in headers]
    for cand in candidates:
        n = _norm(cand)
        for i, h in enumerate(norm_headers):
            if h == n or (n and h.endswith(n)):
                return i
    return None


# ---------------------------------------------------------------------------
# Bottleneck classification
# ---------------------------------------------------------------------------

PRIORITY = {"operator-fallback": "P0", "memory-bound": "P1", "compute-bound": "P1", "communication-bound": "P1"}

RECOMMENDATIONS = {
    "memory-bound": [
        "Reduce memory traffic: fuse elementwise ops, use in-place kernels, or process in tiles that fit in on-chip storage.",
        "Improve data locality: prefer BNSD/BSND layouts that map to contiguous on-chip memory.",
        "Check if FP16/BF16 or block-based (zag) formats cut bytes moved per element.",
        "Raise memory write efficiency by fusing producer/consumer ops into one kernel.",
    ],
    "compute-bound": [
        "Check the tile/tiling parameters: increase M/N/K block size so MAC units stay busy.",
        "Confirm the operator runs an AI Core native kernel (not vector fallback).",
        "Consider operator fusion to increase arithmetic intensity and reuse.",
        "Verify precision: BF16/FP16 achieves the peak vs. FP32 (half the peak).",
    ],
    "communication-bound": [
        "Enable/check HCCL collective optimizations (AllReduce ring vs. tree, fused comm ops).",
        "Overlap communication with computation (pipeline the computation graph).",
        "Reduce message volume by gradient accumulation / compression.",
        "Align ranks and ensure the topology (HCCS vs. PCIe) matches the collective pattern.",
    ],
    "operator-fallback": [
        "The operator did not run an AI Core kernel; banish it to a native custom/ascendc operator if possible.",
        "Check operator compatibility with the NPU (precision/format/constraints).",
        "Aggregate many small fallback ops into a fused native kernel to cut AI CPU overhead.",
    ],
}


def _ratio(value: Optional[float], total: Optional[float]) -> Optional[float]:
    if value is None or total is None or total <= 0:
        return None
    return value / total


def classify_operator(
    duration_us: Optional[float],
    ai_core_us: Optional[float],
    vector_us: Optional[float],
    ai_cpu_us: Optional[float],
    cpu_us: Optional[float],
    mem_read_bytes: Optional[float],
    mem_write_bytes: Optional[float],
    peak_mem_bw_gbs: Optional[float],
    peak_tflops: Optional[float],
    flops: Optional[float],
    name: str = "",
    op_type: str = "",
    threshold_bw: float = 0.6,
) -> Dict:
    """Classify one operator row into bottleneck category(-ies)."""
    total_s = None
    if duration_us is not None:
        total_s = duration_us * 1e-6

    compute_us = ai_core_us if ai_core_us is not None else vector_us
    fallback_us = (ai_cpu_us or 0.0) + (cpu_us or 0.0)

    labels: List[str] = []
    reasons: List[str] = []

    # --- communication-bound ---------------------------------------------
    comm_markers = ("hcc", "allreduce", "all_reduce", "allgather", "all_gather",
                    "reducescatter", "reduce_scatter", "broadcast", "sendrecv",
                    "send_recv", "collective", "cc_", "hccl")
    lower_name = (name + " " + op_type).lower()
    is_collective = any(m in lower_name for m in comm_markers)
    if is_collective:
        labels.append("communication-bound")
        reasons.append("operator/type matches collective communication pattern")

    # --- operator-fallback ------------------------------------------------
    if total_s is not None and fallback_us > 0 and fallback_us / (fallback_us + (compute_us or 0.0)) > 0.5:
        labels.append("operator-fallback")
        reasons.append(f"AI CPU/CPU time ({fallback_us:.2f}us) dominates, no AI Core native kernel")

    # --- memory vs compute ------------------------------------------------
    mem_bytes = (mem_read_bytes or 0.0) + (mem_write_bytes or 0.0)
    achieved_bw_gbs = None
    mem_util = None
    if total_s is not None and total_s > 0 and mem_bytes > 0:
        achieved_bw_gbs = (mem_bytes / 1e9) / total_s
        if peak_mem_bw_gbs:
            mem_util = achieved_bw_gbs / peak_mem_bw_gbs

    achieved_tflops = None
    compute_util = None
    if total_s is not None and total_s > 0 and flops is not None:
        achieved_tflops = (flops / 1e12) / total_s
        if peak_tflops:
            compute_util = achieved_tflops / peak_tflops

    if not is_collective and total_s is not None:
        mem_high = (mem_util is not None and mem_util >= threshold_bw)
        sub_peak = (compute_util is not None and compute_util < 0.5)
        if mem_high and sub_peak:
            labels.append("memory-bound")
            reasons.append(f"memory BW util {mem_util:.0%} vs compute util {compute_util if compute_util is not None else 0:.0%}")
        elif mem_high and (compute_util is None):
            labels.append("memory-bound")
            reasons.append(f"memory BW util {mem_util:.0%} while flops unknown")
        elif compute_util is not None and compute_util >= 0.6:
            labels.append("compute-bound")
            reasons.append(f"compute util {compute_util:.0%} close to hardware peak")
        elif compute_util is not None and compute_util < 0.2 and mem_util is not None and mem_util < 0.3:
            reasons.append("both utilizations low — likely launch/latency or dimension mismatch")
            labels.append("compute-bound")

    if not labels:
        labels.append("compute-bound")
        reasons.append("default: no dominating memory/communication/fallback signal")

    unique = list(OrderedDict.fromkeys(labels))
    return {
        "operator": name or op_type or "unknown",
        "duration_us": duration_us,
        "achieved_tflops": achieved_tflops,
        "compute_util": compute_util,
        "achieved_memory_bw_gbs": achieved_bw_gbs,
        "memory_util": mem_util,
        "bottleneck": unique,
        "priority": min((PRIORITY.get(l, "P2") for l in unique), key=lambda p: int(p[1])),
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def _field(row: Dict[str, str], col: Optional[int], headers: List[str]) -> Optional[float]:
    if col is None or col >= len(headers):
        return None
    raw = row.get(headers[col], "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def diagnose_csv(path: str, peak_tflops: Optional[float], peak_mem_bw_gbs: Optional[float],
                 threshold_bw: float) -> List[Dict]:
    results: List[Dict] = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV {path} has no header row")
        headers = list(reader.fieldnames)

        col_name = _find_col(headers, "Op Name", "op_name", "operator", "name")
        col_type = _find_col(headers, "Op Type", "op_type", "type")
        col_dur = _find_col(headers, "Task Duration(us)", "Duration(us)", "Task Duration",
                            "duration_us", "duration")
        col_ai_core = _find_col(headers, "AI Core Time(us)", "AIC Time(us)", "ai_core_time",
                                "AI Core Time")
        col_vector = _find_col(headers, "Vector Time(us)", "AIV Time(us)", "Vector Time",
                               "vector_time")
        col_ai_cpu = _find_col(headers, "AI CPU Time(us)", "AI CPU Time", "aicpu_time")
        col_cpu = _find_col(headers, "CPU Time(us)", "CPU Time", "cpu_time")
        col_mem_read = _find_col(headers, "Memory Read Bytes", "memory_read_bytes",
                                 "Mem Read Bytes", "Read Bytes")
        col_mem_write = _find_col(headers, "Memory Write Bytes", "memory_write_bytes",
                                  "Mem Write Bytes", "Write Bytes")
        col_flops = _find_col(headers, "FLOPs", "flops", "Operation Compute", "operation_compute")

        if col_dur is None and col_ai_core is None:
            raise ValueError(
                "No duration column found (expected 'Task Duration(us)' or 'Duration(us)'). "
                "Feed a profiling CSV such as OpBasicInfo.csv exported by msprof."
            )

        for row in reader:
            duration_us = _field(row, col_dur, headers)
            if col_dur is None:
                duration_us = _field(row, col_ai_core, headers)

            flops = _field(row, col_flops, headers)
            if flops is not None and "e" not in str(flops):
                # tolerate raw counts
                pass

            r = classify_operator(
                duration_us=duration_us,
                ai_core_us=_field(row, col_ai_core, headers),
                vector_us=_field(row, col_vector, headers),
                ai_cpu_us=_field(row, col_ai_cpu, headers),
                cpu_us=_field(row, col_cpu, headers),
                mem_read_bytes=_field(row, col_mem_read, headers),
                mem_write_bytes=_field(row, col_mem_write, headers),
                peak_mem_bw_gbs=peak_mem_bw_gbs,
                peak_tflops=peak_tflops,
                flops=flops,
                name=row.get(headers[col_name], "") if col_name is not None else "",
                op_type=row.get(headers[col_type], "") if col_type is not None else "",
                threshold_bw=threshold_bw,
            )
            results.append(r)

    # sort by priority, then by duration descending (most expensive first)
    results.sort(key=lambda r: (int(r["priority"][1]), -(r["duration_us"] or 0)))
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render_report(results: List[Dict]) -> str:
    lines: List[str] = []
    lines.append("Bottleneck Diagnosis (sorted by priority, then duration)")
    lines.append("")
    lines.append(f"{'PRIORITY':<9} {'BOTTLENECK':<20} {'DURATION(us)':<14} {'MEM_BW(GB/s)':<14} {'COMPUTE_UTIL':<14} OPERATOR")
    for r in results:
        dur = f"{r['duration_us']:.1f}" if r["duration_us"] is not None else "-"
        bw = f"{r['achieved_memory_bw_gbs']:.1f}" if r["achieved_memory_bw_gbs"] is not None else "-"
        cu = f"{r['compute_util']:.2%}" if r["compute_util"] is not None else "-"
        lines.append(
            f"{r['priority']:<9} {','.join(r['bottleneck']):<20} {dur:<14} {bw:<14} {cu:<14} {r['operator'][:60]}"
        )
    lines.append("")
    for label in ("memory-bound", "compute-bound", "communication-bound", "operator-fallback"):
        recs = RECOMMENDATIONS[label]
        lines.append(f"[{label}] recommendations:")
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-classify Ascend operator bottlenecks from profiling CSV."
    )
    parser.add_argument("--csv", required=True,
                        help="Path to profiling CSV (e.g. OpBasicInfo.csv from msprof).")
    parser.add_argument("--peak-tflops", type=float, default=None,
                        help="Hardware peak FP16/BF16 TFLOPS (e.g. 910B3: 294.91). Used to compute compute utilization.")
    parser.add_argument("--peak-memory-bw", type=float, default=None,
                        help="Hardware peak memory bandwidth in GB/s (e.g. 1200). Used to compute memory utilization.")
    parser.add_argument("--threshold-bw", type=float, default=0.6,
                        help="Memory bandwidth utilization threshold to classify as memory-bound (default 0.6).")
    args = parser.parse_args(argv)

    try:
        results = diagnose_csv(args.csv, args.peak_tflops, args.peak_memory_bw, args.threshold_bw)
    except Exception as exc:  # noqa: B902 - report readable error
        print(f"[bottleneck-diagnoser] ERROR: {exc}", file=sys.stderr)
        return 2

    if not results:
        print("[bottleneck-diagnoser] No operator rows found in CSV.", file=sys.stderr)
        return 1

    print(render_report(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())