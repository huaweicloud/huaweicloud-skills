# Troubleshooting

## 1. Compilation Issues

### Issue: Header file not found

**Symptom:** `fatal error: ascendc/kernel.h: No such file or directory`

**Solution:**
```bash
# Set include path
export ASCEND_INCLUDE_PATH=/usr/local/Ascend/ascend-toolkit/latest/compiler/include
export CPLUS_INCLUDE_PATH=$ASCEND_INCLUDE_PATH:$CPLUS_INCLUDE_PATH

# Or use cmake with proper include paths
```

### Issue: Linker error undefined reference

**Symptom:** `undefined reference to 'ascendc::xxx'`

**Solution:**
```bash
# Link with ascendc library
export ASCEND_LIB_PATH=/usr/local/Ascend/ascend-toolkit/latest compiler/lib64
export LD_LIBRARY_PATH=$ASCEND_LIB_PATH:$LD_LIBRARY_PATH

# Or update CMakeLists.txt
target_link_libraries(op_test ascendc)
```

### Issue: CMake not finding toolchain

**Symptom:** `Could not find toolchain`

**Solution:**
```bash
# Set toolchain file
cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain.cmake ..

# Or verify toolchain path
cat toolchain.cmake | grep CMAKE_C_COMPILER
```

## 2. Runtime Issues

### Issue: ACL initialization failed

**Symptom:** `aclError: 1`

**Solution:**
```bash
# Set ACL config path
export ASCEND_CONFIG_PATH=/usr/local/Ascend/ascend-toolkit/latest/
export LD_LIBRARY_PATH=$ASCEND_CONFIG_PATH/acllib/lib64:$LD_LIBRARY_PATH

# Initialize before running
aclInit(nullptr);
```

### Issue: Memory allocation failed

**Symptom:** `Failed to allocate Tensor`

**Solution:**
```cpp
// Check available memory
// Reduce buffer sizes
// Free unused buffers before allocation
```

### Issue: Kernel launch failed

**Symptom:** `Kernel launch error`

**Solution:**
```bash
# Check NPU status
npu-smi info

# Verify operator compiled for correct chip
# Check soc-version matches hardware
```

## 3. Profiling Issues

### Issue: OPPROF directory not created

**Root Cause:** Insufficient permissions or wrong path

**Solution:**
```bash
# Use absolute path
msprof op --output=/tmp/opprof ./execute_op

# Check directory permissions
chmod 777 /tmp/opprof
```

### Issue: Profiling data incomplete

**Root Cause:** Application crashes or too short execution

**Solution:**
```bash
# Increase iteration count
# Add warmup loop
# Extend execution time
```

## 4. Optimization Issues

### Issue: Performance not improved

**Possible Causes:**
1. Optimization target incorrect
2. Change too small to measure
3. Bottleneck elsewhere

**Solution:**
```bash
# Re-profile to confirm bottleneck
msprof op --aic-metrics=Roofline --output=./opprof ./execute_op

# Check PipeUtilization forPipelineline efficiency
# Check Memory forbandwidthwidth bottlenecks
```

### Issue: Accuracy degraded

**Root Cause:** Wrong optimization logic

**Solution:**
```bash
# Revert changes
cp operator_dir_backup_*/op_kernel/*.cpp operator_dir/op_kernel/

# Rebuild and retest
bash build.sh
./execute_op
```

### Issue: Anti-pattern violation not detected

**Root Cause:** Not checking all rules

**Solution:**
```bash
# Review anti-pattern checklist:
# - FP16/BF16 for complex math
# - No right-value in EXEC_KERNEL_CMD
# - No GM<->UB DataCopy
# - No reuse after ReduceSum/ReduceMax
# - No std::min/max/sqrt/exp in kernel
```

## 5. Debug Commands

```bash
# Check environment
echo $ASCEND_TOOLKIT_HOME
echo $LD_LIBRARY_PATH

# Verify headers
ls /usr/local/Ascend/ascend-toolkit/latest/compiler/include/ascendc/

# Test basic operator
./execute_op

# Check output format
cat op_output.json
```

## Quick Diagnostic

```bash
#!/bin/bash
echo "=== Environment ==="
cmake --version 2>/dev/null || echo "cmake: NOT FOUND"
aarch64-linux-gnu-g++ --version 2>/dev/null | head -1 || echo "compiler: NOT FOUND"

echo "=== Source ==="
ls -la op_kernel/*.cpp 2>/dev/null || echo "No kernel source"

echo "=== Build ==="
bash build.sh 2>&1 | tail -5

echo "=== Run ==="
./execute_op 2>&1 | tail -10
```
