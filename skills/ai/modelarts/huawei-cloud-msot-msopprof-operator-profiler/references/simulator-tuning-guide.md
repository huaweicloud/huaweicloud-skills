# Simulator Tuning Guide

This document focuses on **`msprof op simulator`**. It is suitable for scenarios
without real hardware, or when instruction-level analysis is needed.

## 1. Scope and Mode Boundaries

### Questions Suitable for Simulator

- Is there a bubble in the instruction pipeline?
- Are MTE and VECTOR/CUBE properly parallel?
- Are SET_FLAG/WAIT_FLAG causing waits?
- Which code paths and instructions have highest time?
- Do you need per-core breakdown, per-core `trace.json`, IO rate waveform?

### Common Confusions to Avoid

- Simulator `--aic-metrics` only supports:
  - `PipeUtilization`
  - `ResourceConflictRatio`
  - `PMSampling`
- `TimelineDetail` is a **device mode** feature, not a simulator parameter
- Simulator `trace.json` is **instruction pipeline view**; device `trace.json`
  is compute/communication pipeline

## 2. Pre-Start Checks

### 2.1 How to Specify Simulator Type

Two methods:

1. `--soc-version=Ascendxxxyy`
2. `LD_LIBRARY_PATH=${INSTALL_DIR}/tools/simulator/Ascendxxxyy/lib:$LD_LIBRARY_PATH`

Notes:

- `application`/`export`: Both methods work
- `config`: Use `LD_LIBRARY_PATH`; `--soc-version` is not valid here

### 2.2 Is `-g` Needed?

If you need **code path mapping, call stack, or source-level profiling**,
compile with `-g`.

### 2.3 Is Build Simulator-Compatible?

Not all projects can directly run "device executable" in simulation:

- Some official examples/projects can run on both device and simulator
- Some template libraries or build rules require explicit simulator build

If you encounter `signal 6`, `Bad address`, `std::__ios_failure`, see
`experiences/simulator-needs-sim-build.md`.

## 3. Data Collection Modes

### 3.1 Application Mode

```bash
# Method 1: Explicit simulator type
msprof op simulator --soc-version=Ascend910B4 \
  --output=./output_sim ./execute_add_op

# Method 2: Via environment variable
export LD_LIBRARY_PATH=${INSTALL_DIR}/tools/simulator/Ascend910B4/lib:$LD_LIBRARY_PATH
msprof op simulator --output=./output_sim ./execute_add_op
```

### 3.2 Config Mode

```bash
export LD_LIBRARY_PATH=${INSTALL_DIR}/tools/simulator/Ascend910B4/lib:$LD_LIBRARY_PATH
msprof op simulator --config=./add_test.json --output=./output_sim
```

Notes:

- Under `--config`, no need for `--soc-version`
- `--kernel-name` is not valid for `--config`

### 3.3 Export Mode (Parse Existing dump)

```bash
msprof op simulator --soc-version=Ascend910B4 \
  --export=./dump_dir --output=./output_sim
```

`--export` directory requirements:

- Should contain dump data and related kernel files
- For code path mapping, should include `aicore_binary.o`
- Pure dump without `aicore_binary.o` still allows pipeline parsing,
  but no code mapping

## 4. Simulator-Specific Parameters

### --soc-version

Check `${INSTALL_DIR}/tools/simulator/` directory names, e.g.:

- `Ascend910B4`
- `Ascend910_9391`
- `Ascend310B4`
- `Ascend950`

### --timeout

For "large operator, long simulation" scenarios:

```bash
msprof op simulator --soc-version=Ascend910B4 \
  --timeout=5 --output=./output_sim ./app
```

Notes:

- Unit is minutes, range `[1, 2880]`
- On timeout, tool kills simulation process and proceeds to parsing

### --core-id

Parse specific cores only, useful for evenly distributed operators:

```bash
msprof op simulator --soc-version=Ascend910B4 \
  --core-id="0|31" --output=./output_sim ./app
```

Notes:

- Range `[0, 49]`
- Only affects parsing, not simulation
- **Not valid for `PMSampling`**

### --dump

```bash
msprof op simulator --soc-version=Ascend910B4 \
  --dump=on --output=./output_sim ./app
```

Notes:

- Default `off`
- For A2/A3, controls whether to keep dump
- For some Atlas products, parameter may not apply; dump follows normal process
- Only for single-process scenarios

## 5. Metrics and Views

### Default Metrics

Simulator default provides:

- `PipeUtilization`
- `ResourceConflictRatio`

Meaning: Even without `--aic-metrics`, you get basic pipeline view and
sync details.

### PipeUtilization

- Shows instruction pipeline only
- Good for first look at overall execution order

### ResourceConflictRatio

- Beyond pipeline, provides SET/WAIT FLAG sync details
- Good for analyzing sync waits or conflicts

### PMSampling

```bash
msprof op simulator --soc-version=Ascend910B4 \
  --aic-metrics=PMSampling --output=./output_sim ./app
```

Purpose:

- Shows memory path IO rate waveform
- Key paths:
  - `GM <-> L1`
  - `GM <-> UB`
  - `GM <-> other`

Notes:

- Not enabled by default
- Parses all cores; `--core-id` has no effect

## 6. Output Structure

### Single Operator Common Structure

```text
OPPROF_{timestamp}_XXX/
├── dump/
└── simulator/
    ├── core0.veccore0/
    │   ├── core0.veccore0_code_exe.csv
    │   ├── core0.veccore0_instr_exe.csv
    │   └── trace.json
    ├── core0.veccore1/
    │   ├── core0.veccore1_code_exe.csv
    │   ├── core0.veccore1_instr_exe.csv
    │   └── trace.json
    ├── ...
    ├── visualize_data.bin
    └── trace.json
```
