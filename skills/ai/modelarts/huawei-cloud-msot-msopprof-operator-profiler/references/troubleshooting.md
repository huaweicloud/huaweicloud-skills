# Troubleshooting

## 1. Command Execution Issues

### Issue: msprof command not found

**Symptom:** `msprof: command not found`

**Solution:**

```bash
# Check installation
which msprof

# Source environment
source /usr/local/Ascend/ascend-toolkit/latest/set_env.sh

# Or add to PATH
export PATH=$PATH:/usr/local/Ascend/ascend-toolkit/latest/compiler/bin
```

### Issue: msprof op permission denied

**Symptom:** `Permission denied: ./execute_op`

**Solution:**

```bash
# Fix permissions
chmod 755 ./execute_op

# Check SELinux (if applicable)
getenforce
setenforce 0  # Temporarily disable if needed
```

## 2. Device Mode Issues

### Issue: --kernel-name not effective

**Root Cause:** `--kernel-name` only works with application mode

**Solution:**

```bash
# Verify you're using application mode
msprof op --kernel-name="Add" --output=./output ./execute_op  # Correct

# For config mode, use json matching instead
msprof op --config=./test.json --output=./output
```

### Issue: signal 6 error

**Symptom:** `Program terminated with signal 6`

**Root Cause:** Usually application crash, not msprof issue

**Solution:**

```bash
# Run application directly first
./execute_op

# Check application logs
# Fix application bugs before profiling
```

### Issue: TimelineDetail not available

**Root Cause:** TimelineDetail only for specific chips/modes

**Solution:**

```bash
# Check supported capabilities
msprof op --help | grep -i timeline

# Use Default instead
msprof op --aic-metrics=Default --output=./output ./execute_op
```

## 3. Simulator Mode Issues

### Issue: signal 6 / Bad address

**Symptom:** `signal 6` or `Bad address` during simulation

**Root Cause:** Simulator may need sim-compatible build

**Solution:**

```bash
# Check simulator build requirements
# Some operators need special compilation for simulation

# Try with --dump disabled
msprof op simulator --soc-version=Ascend910B4 \
  --output=./output --dump=off ./execute_op
```

### Issue: --soc-version not effective

**Root Cause:** --soc-version only works with application/export, not config

**Solution:**

```bash
# For config mode, use LD_LIBRARY_PATH
export LD_LIBRARY_PATH=${INSTALL_DIR}/tools/simulator/Ascend910B4/lib:$LD_LIBRARY_PATH
msprof op simulator --config=./test.json --output=./output
```

### Issue: --core-id not working for PMSampling

**Root Cause:** --core-id does not filter PMSampling output

**Solution:**

```bash
# Run without --core-id for full PMSampling
msprof op simulator --aic-metrics=PMSampling \
  --output=./output ./execute_op

# Parse results to filter specific core
grep "core0" output/simulator/core0.*/instr_exe.csv
```

## 4. Output Issues

### Issue: OPPROF directory not created

**Root Cause:** Permission or path issue

**Solution:**

```bash
# Use absolute path
msprof op --output=/tmp/profiling ./execute_op

# Check directory permissions
mkdir -p /tmp/profiling
chmod 777 /tmp/profiling
```

### Issue: CSV files missing

**Root Cause:** Collection too short or metrics not enabled

**Solution:**

```bash
# Use Default metrics explicitly
msprof op --aic-metrics=Default --output=./output ./execute_op

# Increase iteration count
msprof op --launch-count=100 --output=./output ./execute_op
```

### Issue: visualize_data.bin empty

**Root Cause:** Visualization metrics not collected

**Solution:**

```bash
# Collect with Roofline or Occupancy
msprof op --aic-metrics=Roofline --output=./output ./execute_op

# Check file size
ls -la output_npu/visualize_data.bin
```

## 5. Performance Issues

### Issue: Profiling too slow

**Solution:**

```bash
# Reduce launch count
msprof op --launch-count=10 --output=./output ./execute_op

# Use simulator for quick iteration
msprof op simulator --output=./output ./execute_op

# Skip unnecessary metrics
msprof op --aic-metrics=BasicInfo --output=./output ./execute_op
```

### Issue: Output too large

**Solution:**

```bash
# Limit core analysis
msprof op --core-id=0 --output=./output ./execute_op

# Use timeout
msprof op --timeout=60 --output=./output ./execute_op
```

## Quick Diagnostic Commands

```bash
# Check msprof version
msprof --version

# Check help
msprof op --help

# List supported metrics
msprof op --help | grep -A50 "aic-metrics"

# Test basic profiling
msprof op --output=/tmp/test ./execute_op

# Check output
ls -la /tmp/test/
```
