---
name: huawei-cloud-ascend-small-model-migrate
description: |
  Migrate vision/detection/segmentation small models to Ascend NPU, covering the full workflow: model structure analysis, migration verification, performance profiling, and optimization. Based on torch_npu and msprof
  Use this skill when the user wants to: (1) migrate encoder-only models like ResNet, YOLO, UNet to Ascend NPU, (2) analyze model structure for migration feasibility, (3) verify model inference on NPU, (4) identify performance bottlenecks and get optimization suggestions
  Trigger: user mentions "migrate", "migration", "Ascend", "NPU", "YOLO", "ResNet", "encoder-only", "detection", "segmentation", "adaptation", "adapt", "迁移", "昇腾迁移", "小模型", "适配", "昇腾适配", "GPU迁移", "NPU适配", "适配NPU", "适配昇腾"
compatibility:
  - torch_npu >= 2.0.0
  - msprof >= 7.0.0
tags: [Ascend, migration, model, NPU]
allowed-tools:
  - docker
  - python3
  - ssh
---

# Huawei Cloud Ascend Small Model Migration

## Overview

This skill guides the migration workflow for small vision models to Ascend NPU, covering structure analysis → migration verification → performance optimization.

**Architecture**: Model Analysis → Environment Setup → NPU Inference → Performance Profiling → Bottleneck Analysis → Optimization Recommendations

**Related Skills**:
- `huawei-cloud-msmodelslim-model-analysis` - Model structure analysis for migration path determination
- `huawei-cloud-msot-msopprof-operator-profiler` - Operator performance data collection
- `huawei-cloud-ascend-profiler-db-explorer` - Profiling database analysis for bottleneck identification
- `huawei-cloud-ascendc-operator-performance-optim` - Optional: AscendC operator optimization for bottleneck operators

## Architecture Components

This skill involves the following cloud services and components:
- **Ascend NPU**: Target hardware for model deployment (Ascend 910B series)
- **torch_npu**: PyTorch adapter for Ascend NPU
- **MSProf**: Ascend profiling tool for performance analysis
- **Ultralytics**: YOLO model framework support
- **Docker**: Container environment for consistent deployment

## Use Cases

**Typical Problem Scenarios:**
- Migrating vision models from GPU to Ascend NPU
- Deploying YOLO/ResNet/UNet models on Ascend hardware
- Optimizing small model performance on NPU
- Verifying model accuracy after migration
- Identifying performance bottlenecks in computer vision models

**Typical User Phrases:**
- "Migrate YOLOv8 to Ascend NPU
- "How to run ResNet on Ascend?
- "Optimize UNet inference on NPU
- "Verify model accuracy after migration
- "Analyze performance bottlenecks in my vision model
- "YOLOModelMigrationAscendNPU
- "AscendModel？
- "ModelMigrationNPU？

## Scope

**Supported**:
- Encoder-only architectures (ResNet, VGG, EfficientNet)
- Detection models (YOLO, Faster-RCNN, SSD)
- Segmentation models (UNet, DeepLab)
- Other non-Decoder-only LLM models

**Not supported**:
- Decoder-only LLM (Qwen, LLaMA, DeepSeek) - requires adapter-based quantization approach
- Understanding VLM text backbone - requires adapter-based quantization approach

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Model Structure Analysis                           │
│  → Determine msmodelslim compatibility                      │
│  → Output structure analysis + migration path suggestion    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Environment Preparation + Migration Verification  │
│  → Configure torch_npu environment                         │
│  → Run inference test                                      │
│  → Verify accuracy                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Performance Data Collection                       │
│  → Collect operator performance data                       │
│  → Output performance data location                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Performance Analysis                              │
│  → Analyze profiling data for bottlenecks                  │
│  → Output complete operator time distribution              │
│  → Identify bottleneck and well-performing operators       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Optimization Suggestions                          │
│  → Provide optimization solutions for bottleneck operators │
│  → Optional operator optimization                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Model Structure Analysis

### 1.1 Analysis Process

Read the model configuration to analyze:
- Model implementation source (transformers or local directory)
- Architecture type (Decoder-only / Encoder-only / Encoder-Decoder)
- Layer-by-layer loading requirements
- MoE fused weight risks

### 1.2 Migration Path Determination

| Architecture Type | Recommended Path |
|-------------------|------------------|
| Decoder-only LLM | Adapter-based quantization |
| Understanding VLM text backbone | Adapter-based quantization |
| Encoder-only / Detection / Segmentation | Continue with this skill |
| Other | Manual determination required |

### 1.3 Output Analysis Report

```markdown
## Model Structure Analysis Result

### Basic Information
- Model Name: xxx
- Architecture Type: Encoder-only / Decoder-only / Encoder-Decoder
- Parameter Count: xxx
- Source: transformers / local directory

### Support Status
- msmodelslim Support: Yes/No
- Recommended Migration Path: torch_npu direct migration / msmodelslim adaptation

### Migration Suggestions
[Specific recommendations]
```

---

## Step 2: Environment Preparation + Migration Verification

### 2.1 Default Verification Environment

- **Server**: ascend-server-01
- **Container**: skill-the
- **Image**: quay.io/ascend/vllm-ascend:v0.18.0
- **NPU**: 8× Ascend 910B3

### 2.2 Environment Configuration

```bash
# Enter container
docker exec -it skill-the bash

# Install dependencies
pip install torch_npu
pip install ultralytics  # For YOLO series
# Or other model-specific libraries

# OpenCV dependencies (if needed)
apt install libgl1 libglib2.0-0
```

### 2.3 Migration Verification Script

```python
import torch
import torch_npu

# Check NPU availability
print(f"NPU available: {torch.npu.is_available()}")
print(f"NPU count: {torch.npu.device_count()}")

# Load model
model = ...  # Model loading code
model = model.to('npu:0')

# Inference test
with torch.no_grad():
    output = model(input_tensor)

print(f"Inference success: {output is not None}")
```

### 2.4 Output Migration Verification Report

```markdown
## Migration Verification Result

### Environment Information
- Server: ascend-server-01
- Container: skill-the
- torch_npu Version: xxx
- NPU Status: Normal

### Inference Test
- Model Loading: Success/Failure
- NPU Inference: Success/Failure
- Accuracy Verification: Pass/Fail

### Performance Metrics
- Average Inference Time: xxx ms
- FPS: xxx
```

---

## Step 3: Performance Data Collection

### 3.1 Performance Collection Process

Collect operator performance data using the profiling skill:
- On-board collection (device mode)
- Or simulation collection (simulator mode)

### 3.2 Output Performance Data Location

```markdown
## Performance Collection Result

### Data Location
- Server: ascend-server-01
- Path: /home/xxx/PROF_xxx/
- Database: msprof_xxx.db
- Collection Time: xxx

### Collection Configuration
- Mode: device / simulator
- NPU: npu:0
- Collection Duration: xxx s
```

---

## Step 4: Performance Analysis

### 4.1 Analysis Process

Query and analyze:
1. Top N operator time consumption
2. Group statistics by operator type
3. AI_CPU / AI_CORE / AI_VECTOR_CORE distribution

### 4.2 SQL Query Example

```sql
-- Top 20 operators by time
SELECT op_name, op_type, total_time, call_times
FROM op_summary
ORDER BY total_time DESC
LIMIT 20;

-- Group by type
SELECT op_type, SUM(total_time) as type_time, COUNT(*) as count
FROM op_summary
GROUP BY op_type
ORDER BY type_time DESC;
```

### 4.3 Output Performance Analysis Report

```markdown
## Performance Analysis Result

### Operator Time Distribution (TOP 20)
| Rank | Operator Name | Type | Time(ms) | Percentage | Call Count |
|------|--------------|------|----------|------------|------------|
| 1 | xxx | AI_CPU | xxx | xx% | xxx |
| ... | ... | ... | ... | ... | ... |

### Statistics by Type
| Type | Total Time | Percentage | Operator Count |
|------|------------|------------|----------------|
| AI_CPU | xxx | xx% | xxx |
| AI_CORE | xxx | xx% | xxx |
| AI_VECTOR_CORE | xxx | xx% | xxx |

### Bottleneck Operators (>5% usage)
| Operator | Type | Percentage | Issue |
|----------|------|------------|-------|
| xxx | AI_CPU | xx% | [Specific issue] |

### Well-performing Operators
| Operator | Type | Description |
|----------|------|-------------|
| Conv2D | AI_CORE | High Cube utilization, normal |
```

---

## Step 5: Optimization Suggestions

### 5.1 Common Bottlenecks and Solutions

| Bottleneck Type | Cause | Optimization Solution |
|-----------------|-------|----------------------|
| Index operator high time | AI_CPU implementation | Develop optimized version with AscendC |
| TransData high time | Format conversion overhead | Reduce CPU-NPU data transfer |
| NMS fallback to CPU | Operator not NPU supported | Develop NPU version NMS with AscendC |
| Upsample slow | Vector core efficiency | Optimize upsample operator |

### 5.2 Output Optimization Suggestions Report

```markdown
## Optimization Suggestions

### Priority Ranking
| Priority | Operator | Issue | Solution | Expected Gain |
|----------|----------|-------|----------|---------------|
| P0 | xxx | xxx | xxx | xx% |
| P1 | xxx | xxx | xxx | xx% |

### Next Steps
1. [Specific optimization steps]
2. Operator optimization may be performed for bottleneck operators
```

---

## Complete Report Template

After completing each migration task, output a complete report:

```markdown
# [Model Name] Ascend Migration Report

## 1. Model Structure Analysis
[Step 1 output]

## 2. Migration Verification
[Step 2 output]

## 3. Performance Collection
[Step 3 output]

## 4. Performance Analysis
[Step 4 output]

## 5. Optimization Suggestions
[Step 5 output]

## Summary
- Migration Status: Success/Failure
- Inference Performance: xxx ms / xxx FPS
- Main Bottlenecks: xxx
- Optimization Direction: xxx
```

---

## Default Environment

- **Server**: ascend-server-01:22 (root/Hhuawei@smb)
- **Container**: skill-the
- **NPU**: 8× Ascend 910B3 (64G HBM each)
- **CANN**: cann-version-placeholder.220

## Prerequisites

### System Requirements

- Python 3.8+
- torch_npu >= 2.0.0
- msprof >= 7.0.0
- ultralytics >= 8.0.0 (for YOLO models)

### Environment Check

> **Prerequisite check: Python3 + torch_npu + msprof required**
> ```bash
> python3 --version  # Python3 >= 3.8
> python3 -c "import torch_npu; print('OK')"  # NPU PyTorch support
> python3 -c "import msprof; print('OK')"  # Profiling library
> ```
> If not installed: `pip3 install --user torch_npu msprof ultralytics`

### Additional System Dependencies

For computer vision models:
```bash
apt install libgl1 libglib2.0-0  # OpenCV dependencies
```

## Enhanced Features

### Performance Baseline Comparison Module

This skill includes a performance baseline comparison mechanism that compares current model performance against industry-standard baselines:

**Features:**
- **Pre-defined Baselines**: Baseline data for common models (YOLOv8, ResNet50, UNet, EfficientNet) on Ascend NPU
- **Delta Analysis**: Generates performance gap analysis and optimization potential assessment
- **Performance Ranking**: Compares against similar models in the benchmark database
- **Trend Analysis**: Tracks performance improvements across migration iterations

**Baseline Database:**
| Model | Batch Size | Latency (ms) | Throughput (FPS) | Accuracy |
|-------|------------|--------------|------------------|----------|
| YOLOv8n | 32 | 2.3 | 434 | 53.1% mAP |
| YOLOv8s | 16 | 4.8 | 208 | 60.6% mAP |
| ResNet50 | 64 | 1.2 | 533 | 76.1% top-1 |
| UNet | 8 | 8.5 | 94 | - |

**Delta Analysis Output:**
```markdown
## Performance Baseline Comparison
- Target Model: YOLOv8s
- Baseline Reference: YOLOv8s @ Ascend 910B

### Performance Gap
| Metric | Current | Baseline | Gap |
|--------|---------|----------|-----|
| Latency | 5.2 ms | 4.8 ms | +8.3% |
| Throughput | 192 FPS | 208 FPS | -7.7% |
| Accuracy | 60.2% | 60.6% | -0.4% |

### Optimization Potential
- Priority P0: Reduce latency by optimizing Conv operators
- Priority P1: Improve memory access pattern
- Expected Gain: ~10-15% performance improvement
```

### Resource Estimation & Planning Tool

This skill provides pre-migration resource estimation capabilities:

**Features:**
- **Memory Requirements Prediction**: Estimates NPU memory usage based on model size and batch configuration
- **Inference Time Estimation**: Predicts latency and throughput before deployment
- **Batch Size Recommendation**: Suggests optimal batch size based on target latency constraints
- **Multi-card Scaling Guidance**: Provides scaling recommendations for multi-device deployment
- **Cost-Benefit Analysis**: Evaluates optimization investment vs. expected performance gain

**Resource Estimation Output:**
```markdown
## Resource Estimation Report
- Model: YOLOv8s
- Input Resolution: 640x640

### Memory Requirements
| Component | Size |
|-----------|------|
| Model Weights | 21 MB |
| Activation (BS=16) | 480 MB |
| Total Estimated | 501 MB |

### Performance Prediction
| Batch Size | Estimated Latency | Estimated Throughput |
|------------|-------------------|---------------------|
| 8 | 3.2 ms | 250 FPS |
| 16 | 4.8 ms | 208 FPS |
| 32 | 8.5 ms | 188 FPS |

### Recommended Configuration
- Optimal Batch Size: 16
- Target Latency: 4.8 ms
- Expected Throughput: 208 FPS
- Memory Utilization: ~78% of 64GB HBM
```

## Reference Documents

| Document | Description |
|----------|-------------|
| [Acceptance Criteria](references/acceptance-criteria.md) | Functional and non-functional acceptance criteria |
| [Verification Method](references/verification-method.md) | Step-by-step verification guide |
| [Troubleshooting](references/troubleshooting.md) | Common issues and solutions |
| [Report Template](references/report-template.md) | Report generation template |
| [Profiler SQL](references/profiler-sql.md) | SQL query references |
| [Migration Scripts](references/migration-scripts.md) | Migration helper scripts |

## Prerequisites (Duplicate - See Above)

- torch_npu >= 2.0.0 installed
- msprof >= 7.0.0 installed
- Ascend NPU environment configured
- Model code to be migrated

## Core Commands

```bash
# Analyze model migration feasibility
python3 scripts/analyze_model.py --model /path/to/model

# Verify NPU inference
python3 scripts/verify_npu.py --model /path/to/model --input test.jpg
```

## Parameter Confirmation

| Parameter | Description | Required |
|------|------|------|
| model | Model code path | Yes |
| input | Test input data | Yes |
| output | Output directory | No |

