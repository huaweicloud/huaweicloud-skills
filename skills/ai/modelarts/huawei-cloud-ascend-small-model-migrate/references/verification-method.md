# Verification Methods

## Prerequisite Verification

### 1. Verify Server Connectivity

```bash
# Test SSH connection
ssh -p 22 root@ascend-server-01 "echo connected"

# Verify NPU availability
ssh -p 22 root@ascend-server-01 "npu-smi info"

# Check container status
ssh -p 22 root@ascend-server-01 "docker ps | grep skill-the"
```

### 2. Verify Python Environment

```bash
# Inside container
docker exec skill-the bash -c "python3 --version"
docker exec skill-the bash -c "pip list | grep torch"

# Check torch_npu
docker exec skill-the bash -c "python3 -c 'import torch; print(torch.npu.is_available())'"
```

### 3. Verify Model Files

```bash
# Check model directory
ssh -p 22 root@ascend-server-01 "ls -la /path/to/model/"

# Verify model can be loaded
docker exec skill-the bash -c "python3 -c 'import torch; m=torch.load(\"/path/to/model.pt\"); print(type(m))'"
```

## Functional Verification

### 1. Model Structure Analysis

```bash
# Step 1: Call msmodelslim-model-analysis skill
# Read model config
cat /path/to/model/config.json

# Analyze architecture
python3 analyze_model.py --model-path /path/to/model --output analysis_report.md
```

### 2. Environment Setup Verification

```bash
# Enter container
docker exec -it skill-the bash

# Install dependencies
pip install torch_npu
pip install ultralytics  # For YOLO

# Verify installation
python3 -c "import torch_npu; print('torch_npu OK')"
```

### 3. Migration Verification

```python
# Inside container
import torch
import torch_npu

# Check NPU
print(f"NPU available: {torch.npu.is_available()}")

# Load and migrate model
model = ...  # Your model loading code
model = model.to('npu:0')
model.eval()

# Run inference
with torch.no_grad():
    output = model(input_tensor)

print(f"Inference success: {output is not None}")
```

### 4. Performance Profiling

```bash
# Collect performance data
cd /path/to/model
msprof op --output=./profiling_data python3 inference.py

# Analyze results
ls -la profiling_data/
cat profiling_data/OpBasicInfo.csv
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

SERVER="ascend-server-01"
PORT=22
CONTAINER="skill-the"

echo "=== 1. Verify Server Connectivity ==="
ssh -p ${PORT} root@${SERVER} "echo connected"

echo "=== 2. Verify NPU ==="
ssh -p ${PORT} root@${SERVER} "npu-smi info"

echo "=== 3. Verify Container ==="
ssh -p ${PORT} root@${SERVER} "docker ps | grep ${CONTAINER}"

echo "=== 4. Verify Python Environment ==="
docker exec ${CONTAINER} bash -c "python3 --version"
docker exec ${CONTAINER} bash -c "python3 -c 'import torch; print(torch.npu.is_available())'"

echo "=== 5. Test Model Migration ==="
docker exec ${CONTAINER} bash -c "python3 -c 'import torch_npu; print(\"NPU OK\")'"

echo "=== All verifications passed ==="
```

## Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| SSH connection | Connected successfully |
| NPU available | npu-smi returns device info |
| Container running | skill-the container active |
| Python version | >= 3.8 |
| torch_npu installed | Import successful |
| NPU inference | Output tensor valid |
| Profiling data | OPPROF_* directory created |
