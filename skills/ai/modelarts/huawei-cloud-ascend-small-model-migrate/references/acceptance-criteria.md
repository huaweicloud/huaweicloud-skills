# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Model Structure Analysis

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should identify model architecture type | Check output architecture classification |
| AC-1.2 | Should determine migration path | Verify path recommendation |
| AC-1.3 | Should output analysis report | Check report completeness |

### 2. Environment Setup

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should connect to target server | SSH connection test |
| AC-2.2 | Should run in correct container | Docker exec verification |
| AC-2.3 | Should install required dependencies | pip list check |

### 3. Migration Verification

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Model loads successfully on NPU | Check model loading output |
| AC-3.2 | NPU inference produces correct output | Compare with CPU baseline |
| AC-3.3 | Accuracy within acceptable range | Compare results |

### 4. Performance Profiling

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should collect performance data | Check OPPROF_* directory |
| AC-4.2 | Should identify bottleneck operators | Check analysis report |
| AC-4.3 | Should provide optimization suggestions | Check recommendations |

## Correct/Error Pattern Comparison

### Server Connection

**Correct:** Verify server accessibility first
```bash
ssh -p 22 root@ascend-server-01 "echo connected"
ssh -p 22 root@ascend-server-01 "npu-smi info"
```

**Error:** Start migration without server verification
```bash
# Skipping connection test leads to timeout errors later
docker exec skill-the bash -c "pip install ..."
```

### NPU Detection

**Correct:** Verify NPU availability
```python
import torch
print(f"NPU available: {torch.npu.is_available()}")
print(f"NPU count: {torch.npu.device_count()}")
```

**Error:** Assume NPU is available
```python
# Without checking availability
model = model.to('npu:0')  # May fail silently
```

### Model Loading

**Correct:** Load model with proper device mapping
```python
import torch
import torch_npu

model = YourModel()
model = model.to('npu:0')
model.eval()
```

**Error:** Load without NPU conversion
```python
model = YourModel()  # Stays on CPU
output = model(input)  # No NPU acceleration
```

## Non-Functional Acceptance Criteria

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | Migration success rate | > 90% |
| NAC-1.2 | Inference latency (per image) | < 100ms |
| NAC-1.3 | Profiling data collection time | < 5 minutes |

## Test Cases Summary

### Positive Test Cases

1. TC-001: Encoder-only model (ResNet) migration
2. TC-002: Detection model (YOLO) migration
3. TC-003: Segmentation model (UNet) migration
4. TC-004: End-to-end workflow execution
5. TC-005: Performance profiling and analysis

### Negative Test Cases

1. TC-N01: Unsupported model type (Decoder-only LLM)
2. TC-N02: NPU not available on server
3. TC-N03: Container not running
4. TC-N04: Missing dependencies
5. TC-N05: Profiling data collection timeout
