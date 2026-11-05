---
name: huawei-cloud-ascend-op-mfu-calculator
description: |
  Calculate MFU (Machine FLOP Utilization) for operators like matmul/GEMM/FlashAttention on Ascend NPU, providing clear formulas and derivation process
  Use when the user wants to: (1) calculate MFU for matrix operations, (2) analyze operator performance efficiency, (3) bottleneck diagnosis from Ascend profiling data, (4) optimize operator implementation
  Triggers include: "MFU", "machine flop utilization", "operator FLOPs", "matmul performance", "GEMM efficiency", "Ascend MFU", "算子MFU", "算力利用率", "矩阵乘效率", "GEMM性能", "FlashAttention性能", "瓶颈诊断", "bottleneck"
tags: [Ascend, MFU, operator, performance]
compatibility:
  - Python3 >= 3.8
allowed-tools:
  - python3
---

# Huawei Cloud Ascend Operator MFU Calculator

## Overview

This skill calculates MFU (Machine FLOP Utilization) for operators like matmul/GEMM/FlashAttention on Ascend NPU, providing clear formulas and derivation process.

**Architecture**: Input Validation → FLOPs Calculation → Achieved TFLOPs/s → MFU Calculation → Result Analysis

**Related Skills**:
- Profiling data analysis skills may provide operator performance data (execution time and memory traffic) used by this skill's MFU calculation and bottleneck diagnosis.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

1. Python 3.8+ installed
2. Basic understanding of FLOPs calculation concepts
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

> All `hcloud` commands in this skill are wrapped with `skill-quality-cli run` for telemetry. No manual action required.

## Usage Scenarios

**Typical Problem Scenarios**:
- Evaluating how well an operator utilizes Ascend NPU compute power
- Comparing performance of different operator implementations
- Identifying optimization opportunities for matrix operations

**Typical User Utterances**:
- "Calculate MFU for my GEMM operator"
- "What's the machine FLOP utilization for FlashAttention?"
- "Analyze my matmul operator performance efficiency"

## Workflow

1. **Input Collection**: Gather operator parameters (matrix dimensions, data types, execution time)
2. **FLOPs Calculation**: Compute theoretical FLOPs for the operation
3. **Achieved Performance**: Calculate achieved TFLOPs/s from execution time
4. **MFU Calculation**: Apply formula MFU = Achieved FLOPs / Peak FLOPs
5. **Result Analysis**: Provide interpretation and optimization suggestions

## MFU Calculation Formula

MFU = (Achieved FLOPs / Peak FLOPs) × 100%

**Where**:
- Achieved FLOPs = Operation FLOPs / Execution Time
- Peak FLOPs = Hardware-specific peak performance. Use the **per-model** FP16/BF16 peak values below — do NOT use a single generic value like 256 TFLOPs.

| Ascend Model | FP16/BF16 Peak (TFLOPs/s) |
|--------------|---------------------------|
| 910B1 | ≈ 378.88 |
| 910B2 | ≈ 353.89 |
| 910B3 | ≈ 294.91 |
| 910B4 | ≈ 270 |

## Reference Documents

| Document | Description |
| -------- | ----------- |
| [Ascend 910B Series Technical Specifications](https://e.huawei.com/cn/products/computing/ascend-910) | Official Ascend 910B series product specifications |
| [MFU Calculation Methodology](references/mfu-calculation-methodology.md) | Detailed MFU calculation formulas and examples |
| [FlashAttention Technical Paper](https://arxiv.org/abs/2205.14135) | Original FlashAttention research paper |

## Enhanced Features

### Intelligent Bottleneck Diagnoser

A rule-based bottleneck diagnoser (`scripts/bottleneck_diagnoser.py`) that analyzes Ascend profiling CSV data (e.g. `OpBasicInfo.csv` from msprof) and automatically classifies each operator's bottleneck:

- **memory-bound** — achieved memory bandwidth utilization is close to the hardware peak
- **compute-bound** — AI Core (compute) utils are the limiting resource
- **communication-bound** — collective communication operators (HCCL AllReduce/AllGather, etc.) dominate
- **operator-fallback** — the operator ran on AI CPU / CPU instead of an AI Core kernel

It computes per-operator achieved TFLOPS, memory bandwidth and compute utilization, then returns a ranked report (priority P0/P1/P2) with concrete optimization recommendations.

```bash
skill-quality-cli run --skill-name huawei-cloud-ascend-op-mfu-calculator -- python3 scripts/bottleneck_diagnoser.py --csv OpBasicInfo.csv --peak-tflops 294.91 --peak-memory-bw 1200
```

> Column matching is tolerant of the exact msprof header names (e.g. `Task Duration(us)`, `AI Core Time(us)`, `Memory Read Bytes`, `Memory Write Bytes`). If a column is absent, the related signal is skipped and classification falls back to the remaining signals.

## Core Commands

The skill is a pure calculation/diagnosis skill (no Huawei Cloud CLI mutation): everything is computed locally with Python 3.8+.

| Command | Purpose |
|---------|---------|
| MFU calculation | Compute FLOPs, achieved TFLOPs/s and MFU with the formulas in [MFU Calculation Methodology](references/mfu-calculation-methodology.md); use per-model peak TFLOPs from the table above and confirm the execution-time unit (ms vs us) |
| `python3 scripts/bottleneck_diagnoser.py --csv <profiling.csv> [--peak-tflops <TFLOPs>] [--peak-memory-bw <GB/s>]` | Auto-classify operator bottlenecks from Ascend profiling CSV |

## Parameter Confirmation

| Parameter | Description | Required |
|-----------|-------------|----------|
| operator | Operator type (matmul/flash_attention/gemm, etc.) | Yes |
| flops | Theoretical FLOPs of the operator | Yes |
| time_ms | Operator execution time (milliseconds) | Yes |
| time_us | Operator execution time (microseconds) — alternative to `time_ms` | No |
| peak_tflops | Hardware peak computing power (TFLOPS); use the per-model table above | Yes |
| device | NPU device type (910B1/910B2/910B3/910B4/910, etc.) | No |

### Time Unit Handling (ms / us)

MFU is sensitive to the execution-time unit — mixing ms and us changes the result by ~1000×. Follow these rules:

- **`time_ms` is the canonical input (milliseconds).**
- If the user provides the duration from an Ascend profiler (e.g. profiling CSV columns `Task Duration(us)`), that value is in **microseconds (us)** — convert it before calculating:
  - `time_ms = time_us / 1000`
  - Achieved TFLOPs/s = `flops / (time_us × 1e-6) / 1e12`  (equivalently `flops / (time_ms × 1e-3) / 1e12`)
- Alternatively pass `time_us` as the input parameter and let the calculation convert internally.
- Always ask the user to confirm the unit when it is ambiguous, and state the unit in the final MFU result.
