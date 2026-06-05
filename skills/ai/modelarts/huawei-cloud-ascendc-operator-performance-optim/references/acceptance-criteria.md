# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Phase 1: Investigation

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should read operator design documents | Check document access |
| AC-1.2 | Should read source code completely | Verify full code read |
| AC-1.3 | Should identify optimization points by phase | Check investigation report |

### 2. Phase 2: Baseline

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should backup original operator directory | Verify backup exists |
| AC-2.2 | Should collect baseline performance data | Check OPPROF_* directory |
| AC-2.3 | Should generate baseline report | Verify _baseline_report.md |

### 3. Phase 3: Optimization

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should load ascendc-api reference | Check loaded references |
| AC-3.2 | Should follow anti-pattern rules | Verify no violations |
| AC-3.3 | Should compile successfully | Check compilation output |

### 4. Phase 4: Accuracy Verification

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should verify optimized operator accuracy | Check pass output |
| AC-4.2 | Should compare with baseline accuracy | Verify accuracy maintained |

### 5. Phase 5: Performance Verification

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-5.1 | Should collect post-optimization data | Check new OPPROF_* |
| AC-5.2 | Should generate comparison report | Verify _optim_report.md |
| AC-5.3 | Should show performance improvement | Check speedup percentage |

## Correct/Error Pattern Comparison

### Directory Backup

**Correct:** Backup before modification
```bash
# Backup with timestamp
cp -r operator_dir operator_dir_backup_$(date +%Y%m%d%H%M%S)

# Verify backup
ls -la operator_dir_backup_*/
```

**Error:** Modify without backup
```bash
# Direct modification is risky
vi op_kernel/add.cpp  # Lost original if something goes wrong
```

### Anti-Pattern Violations

**Correct:** Cast FP16/BF16 to FP32 for complex math
```cpp
half a = ...;
float a_f = (float)a;
// Use a_f for sqrt/exp/log etc.
float result = expf(a_f);
half result_h = (half)result;
```

**Error:** Direct FP16/BF16 math
```cpp
half a = ...;
// Wrong: exp expects float
half result = exp(a);  // Undefined behavior
```

### Compilation

**Correct:** Use provided build scripts
```bash
bash build.sh
# Or
mkdir build && cd build
cmake .. && make
```

**Error:** Manual compilation without cmake
```bash
g++ -o op op.cpp  # Missing include paths, defines
```

## Non-Functional Acceptance Criteria

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | Speedup ratio | > 10% improvement |
| NAC-1.2 | Accuracy maintained | No degradation |
| NAC-1.3 | Optimization iteration | <= 3 rounds |

## Test Cases Summary

### Positive Test Cases

1. TC-001: Tiling optimization
2. TC-002: Data copy optimization
3. TC-003: API usage optimization
4. TC-004: Memory optimization
5. TC-005: Pipeline optimization
6. TC-006: End-to-end optimization workflow

### Negative Test Cases

1. TC-N01: Modify without backup
2. TC-N02: Violate anti-pattern rules
3. TC-N03: Compilation failure
4. TC-N04: Accuracy degradation
5. TC-N05: Performance not improved
