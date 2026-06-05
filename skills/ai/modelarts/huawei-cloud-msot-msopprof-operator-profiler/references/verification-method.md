# Verification Methods

## Prerequisite Verification

### 1. Verify msprof Installation

```bash
# Check msprof version
msprof --version

# Check msprof op subcommand
msprof op --help

# Verify msprof op simulator
msprof op simulator --help
```

### 2. Verify Environment

```bash
# For device mode: Check NPU availability
npu-smi info

# For simulator mode: Check simulator installation
ls -la ${ASCEND_TOOLKIT_PATH}/tools/simulator/

# Check CANN version
cat /usr/local/Ascend/ascend-toolkit/latest/version.ini
```

### 3. Verify Target Application

```bash
# Check operator executable exists
ls -la ./execute_op

# Test executable runs
./execute_op

# Verify compilation with debug info (for source analysis)
file ./execute_op
```

## Functional Verification

### 1. Mode Selection Verification

```bash
# Test mode determination logic
# User query: "profile operator on real NPU"
# Expected: device mode

# User query: "simulate without hardware"
# Expected: simulator mode
```

### 2. Command Generation Verification

```bash
# Generate command
msprof op --output=./output_npu ./execute_op

# Verify output directory created
ls -la output_npu/

# Check OpBasicInfo.csv generated
cat output_npu/OpBasicInfo.csv
```

### 3. Result Interpretation Verification

```bash
# Read CSV results
head -20 output_npu/OpBasicInfo.csv

# Check key metrics
# - Task Duration (us)
# - aiv_vec_ratio
# - aiv_scalar_ratio

# Verify visualize_data.bin exists
ls -la output_npu/visualize_data.bin
```

### 4. Report Verification

```bash
# Generate report following template
# Should contain:
# 1. Operator Basic Information
# 2. Key Data TOP5
# 3. Core Bottleneck TOP5
# 4. Optimization Suggestions TOP5

# Verify TOP5 items present
grep -c "##" report.md  # Should be 4 sections
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

echo "=== 1. Verify msprof Installation ==="
msprof --version
msprof op --help | head -5

echo "=== 2. Verify NPU (for device mode) ==="
npu-smi info | head -10

echo "=== 3. Verify Target Application ==="
ls -la ./execute_op
file ./execute_op

echo "=== 4. Run Profiling ==="
rm -rf output_npu
msprof op --output=./output_npu ./execute_op

echo "=== 5. Verify Output ==="
ls -la output_npu/
test -f output_npu/OpBasicInfo.csv && echo "OpBasicInfo.csv: OK"
test -f output_npu/PipeUtilization.csv && echo "PipeUtilization.csv: OK"

echo "=== All verifications passed ==="
```

## Verification Checklist

- msprof version: >= 7.0
- msprof op available: Command recognized
- NPU available: npu-smi returns info
- Target executable: Exists and runs
- Output directory: OPPROF_* created
- OpBasicInfo.csv: File exists and readable
- PipeUtilization.csv: File exists
- visualize_data.bin: File exists
- Report sections: 4 required sections present
