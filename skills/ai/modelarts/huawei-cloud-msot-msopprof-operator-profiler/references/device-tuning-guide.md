# Device Tuning Guide

This document focuses on **`msprof op` Device Mode Profiling**. For command-level
pipeline, per-core breakdown, or complex dump analysis, see
`simulator-tuning-guide.md`.

## 1. Scope and Prerequisites

### Scope

- Have real Ascend device available
- Need real hardware metrics: time, bandwidth, cache, roofline, core load,
  compute pipeline, etc.
- Input modes supported:
  - `application`: executable file
  - `config`: JSON + `.o`

### Prerequisites Checklist

1. Application runs correctly before profiling
2. Output path and config path contain no symlinks; parent directory permissions
   match tool requirements
3. If source-level profiling is needed, operator compiled with `-g`
4. If using `range replay`, confirm user code has mstx markers

## 2. Compilation Preparation

If you need **source-level profiling, cache breakdown, or source mapping**,
add debug info during operator compilation:

```bash
# Example: add -g to operator compile configuration
add_ops_compile_options(ALL OPTIONS -g)
```

Then recompile and redeploy the operator package.

> Note: `-g` embeds debug info, which may impact performance. Control access
> permissions accordingly. Official documentation does not support `-O0`.

## 3. Collection Mode Selection

### 3.1 Application Mode

```bash
# Single operator default collection
msprof op --output=./output ./execute_add_op

# Full metrics + Roofline
msprof op --aic-metrics=Roofline,Default --output=./output ./execute_add_op
```

### 3.2 Multi-Operator Application

```bash
# Collect first 10 matching Add/Sub operators
msprof op --launch-count=10 --kernel-name="Add|Sub" --output=./output ./test

# Skip first 3 operators, collect 5 starting from 4th
msprof op --launch-skip-before-match=3 --launch-count=5 --output=./output ./test
```

Notes:

- `--kernel-name` only valid in application mode
- `--launch-skip-before-match` count does not require `kernel-name` first

### 3.3 Config Mode

```bash
msprof op --config=./add_test.json --aic-metrics=Default --output=./output
```

This mode is useful when you cannot directly launch the app but have
JSON + `.o` configuration.

## 4. Replay Mode Selection

- **kernel** (`--replay-mode=kernel`): Default; focus on single operator kernel.
  Most stable.
- **application** (`--replay-mode=application`): Preserve app-level context / L2
  state. May have partial data in `visualize_data.bin`.
- **range** (`--replay-mode=range --mstx=on`): Profile specific operator range.
  Most limitations; check compatibility first.

### Range Mode Limitations

- Must use with `--mstx=on`
- Only supports specific core types (see A2/A3 docs)
- Cannot use with `MemoryDetail`, `TimelineDetail`, `Source` simultaneously
- Not recommended with `--kill=on`
- Check version-specific help for merged operator limitations

## 5. Metric Selection Guide

- **Confirm time anomaly**: `Default` → `OpBasicInfo.csv`, `PipeUtilization.csv`
- **Compute vs memory bound**: `Roofline,Default` → Roofline in
  `visualize_data.bin`
- **Core load imbalance**: `Occupancy,Default` → Per-core time/IO/cache rate
- **Source-level profiling**: `Source,Default` → `visualize_data.bin`
  (needs `-g`)
- **L2 / Memory detail**: `MemoryDetail` → L2 hit rate, GM copy, MTE bandwidth
- **Timeline detail**: `TimelineDetail,Default` → Limited to A2/A3 scenarios
- **Pipe pipeline**: `PipeTimeline` → Atlas 350 only
- **Lightweight basic info**: `BasicInfo` → Only `OpBasicInfo.csv`

## 6. Result Analysis

### 6.1 CSV Quick Analysis

- **OpBasicInfo.csv**: Total time anomaly → Check operator name, block dim,
  total time
- **PipeUtilization.csv**: Compute/copy imbalance → Check per-pipe time ratio
- **ArithmeticUtilization.csv**: Low compute unit utilization → Check
  Cube/Vector time and ratio
- **Memory.csv**: Main path bandwidth issue → Check UB/L1/L2/GM read/write
  bandwidth
- **MemoryUB.csv**: Large block variance → Check core imbalance
- **L2Cache.csv**: Low hit rate → Check L2 Hit/Miss
- **ResourceConflictRatio.csv**: High resource conflict → Check bank conflict
  ratio

### 6.2 visualize_data.bin

Import into MindStudio Insight to view:

- Compute/memory heatmap
- Roofline bottleneck analysis
- Cache heatmap
- Source-level profiling
- Compute pipeline

### 6.3 trace.json

In device mode, `trace.json` is mainly for **compute/communication pipeline**.
Its meaning differs from simulator mode `trace.json`.

## 7. Key Visualization Interpretation

### 7.1 Compute/Memory Heatmap

Focus on three aspects:

1. **Core Load Analysis (Occupancy)**: If max/min differ significantly
   (>10% threshold), load is imbalanced.
2. **Compute Load Analysis**: Check if Cube/Vector utilization is low.
3. **Memory Load Analysis**: Check if MTE path bandwidth is a bottleneck.

### 7.2 Roofline

Use as "bottleneck quick check":

- Point near compute roofline: **Compute Bound**
- Point near bandwidth line: **Memory Bound**
- Neither: May be **Latency Bound**; drill into pipeline/memory/compute

### 7.3 Cache Heatmap

Answers:

- Which source code regions have L2 Hit/Miss anomalies?
- Is low hit rate concentrated in specific regions?

Requires:

- `Source` enabled
- Operator compiled with `-g`
- Core type / operator type supports this view

### 7.4 Source-Level Profiling

Left side shows source code level, right side shows instruction level.
Useful for correlating "high-time code path" with "high-time instruction".

### 7.5 Compute Pipeline

This is often a source of confusion:

- User guide describes supported scope for merged operators
- Pipeline view shows MC2/LCCL/ASC details

Guidance:

- For general questions, say "supports merged operator scenarios"
- For specific operator support, check **version help + version docs**

## 8. Common Errors

1. **Enabling all metrics at once**
   - Correct: Run `Default` first, then add `Roofline`/`Source`/`MemoryDetail`
2. **Treating `TimelineDetail` as default for all profiling**
   - It has many limitations; `Source` is more generally applicable
3. **Permission issues**
   - Tool may fail silently if output/config directory permissions are wrong
4. **Confusing device `trace.json` with simulator pipeline view**
   - Same filename, different meaning

## 9. Recommended Tuning Sequence

1. `Default`: Confirm genuine performance issue exists
2. `Roofline`: Determine high-level direction (compute/memory/latency)
3. `MemoryDetail` or `Source`: Drill down based on direction
4. `Occupancy`: Check core imbalance
5. For compute or core-specific: Check `trace.json`/`PipeTimeline`/`PcSampling`
