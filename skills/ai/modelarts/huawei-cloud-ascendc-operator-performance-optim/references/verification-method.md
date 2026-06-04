# Verification Methods

## Prerequisite Verification

### 1. Verify Development Environment

```bash
# Check CANN installation
cat /usr/local/Ascend/ascend-toolkit/latest/version.ini

# Check AscendC headers
ls -la /usr/local/Ascend/ascend-toolkit/latest/compiler/include/ascendc/

# Verify ACL availability
ls -la /usr/local/Ascend/ascend-toolkit/latest/
```

### 2. Verify Operator Source

```bash
# Check operator directory structure
ls -la operator_dir/
# Expected: op_host/, op_kernel/, CMakeLists.txt

# Check source files
ls -la operator_dir/op_kernel/*.cpp
```

### 3. Verify Build Tools

```bash
# Check cmake
cmake --version

# Check compiler
aarch64-linux-gnu-g++ --version

# Check build script
cat operator_dir/build.sh
```

## Functional Verification

### Phase 1: Investigation Verification

```bash
# Read operator design document
cat operator_dir/design_doc.md

# Read source code
cat operator_dir/op_kernel/add.cpp

# Generate investigation report
# Should list optimization points by phase
```

### Phase 2: Baseline Verification

```bash
# Backup operator directory
cp -r operator_dir operator_dir_backup_$(date +%Y%m%d)

# Run baseline profiling
cd operator_dir
msprof op --output=./baseline_opprof ./execute_op

# Verify baseline report
ls -la *_baseline_report.md
```

### Phase 3: Optimization Verification

```bash
# Verify reference loaded
# Check ascendc-api references

# Apply code modifications
vi op_kernel/add.cpp
vi op_host/add.cpp

# Rebuild
bash build.sh

# Verify compilation
# Should show "Build success" or no errors
```

### Phase 4: Accuracy Verification

```bash
# Run accuracy test
cd operator_dir
./execute_op

# Check output
# Should show "pass" or "accuracy OK"
# Should not show errors

# Compare with baseline
echo "Accuracy verification: PASS"
```

### Phase 5: Performance Verification

```bash
# Collect post-optimization data
cd operator_dir
msprof op --output=./optim_opprof ./execute_op

# Generate comparison
# Should show before/after metrics

# Calculate speedup
# (baseline - optimized) / baseline * 100%
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

echo "=== 1. Verify Environment ==="
cmake --version
aarch64-linux-gnu-g++ --version

echo "=== 2. Verify Operator Source ==="
ls -la operator_dir/op_kernel/*.cpp

echo "=== 3. Backup Original ==="
cp -r operator_dir operator_dir_backup_$(date +%Y%m%d%H%M%S)

echo "=== 4. Build Baseline ==="
cd operator_dir && bash build.sh

echo "=== 5. Run Baseline Profiling ==="
msprof op --output=./baseline ./execute_op

echo "=== 6. Apply Optimizations ==="
# Code modifications here

echo "=== 7. Rebuild ==="
bash build.sh

echo "=== 8. Verify Accuracy ==="
./execute_op

echo "=== 9. Run Post-Optim Profiling ==="
msprof op --output=./optimized ./execute_op

echo "=== All verifications passed ==="
```

## Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| cmake available | >= 3.10 |
| Compiler available | aarch64-linux-gnu-g++ |
| Source files exist | op_kernel/*.cpp |
| Backup created | operator_dir_backup_* exists |
| Baseline OPPROF | OPPROF_* directory |
| Baseline report | *_baseline_report.md |
| Compilation | No errors |
| Accuracy | Output shows pass |
| Optim OPPROF | New OPPROF_* directory |
| Comparison report | *_optim_report.md |
