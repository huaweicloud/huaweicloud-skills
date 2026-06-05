---
name: huawei-cloud-msot-msopprof-operator-profiler
description: |
  Collect operator-level performance data on Ascend NPU using msopprof tool.
  Supports both device mode and simulator mode, generates performance analysis
  reports. Use this skill when the user wants to: (1) profile operator
  performance on Ascend NPU, (2) collect performance data for analysis,
  (3) identify performance bottlenecks through operator execution characteristics.
  Trigger: user mentions "msopprof", "profiler", "performance profiling",
  "operator profiling", "Ascend", "NPU", "profile data", "性能采集",
  "算子性能", "性能剖析", "算子耗时采集"
compatibility:
  - msopprof >= 1.0.0
  - CANN >= 7.0.0
tags: [Ascend, msopprof, profiler, operator]
allowed-tools:
  - python3
  - msopprof
  - bash
---

# Huawei Cloud msOT msopprof Operator Profiler

## Overview

This skill provides operator-level performance profiling capabilities for
Ascend NPU.

**Architecture**: Profiling Configuration → Data Collection → Report Generation
→ Analysis

**Related Skills**:

- `huawei-cloud-ascend-profiler-db-explorer` - Profiling database analysis and
  query
- `huawei-cloud-ascend-small-model-migrate` - Migration workflow that uses
  performance data

## Architecture Components

This skill involves the following cloud services and components:

- **msopprof**: Huawei Cloud operator profiling tool for Ascend NPU
- **CANN**: AI Computing Platform for NPU runtime support
- **Ascend NPU**: Target hardware for performance profiling
- **Profiling Database**: Storage for collected performance data

**Architecture Diagram:**

```text
┌─────────────────────────────────────────────────────────────┐
│           msOT msopprof Operator Profiler Skill            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Profiling   │───▶│  Data        │───▶│  Report      │ │
│  │  Config      │    │  Collection  │    │  Generation  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Mode        │    │  Operator    │    │  Data        │ │
│  │  Selection   │    │  Execution   │    │  Export      │ │
│  │  (Device/Sim)│    │  Monitoring  │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Use Cases

**Typical Problem Scenarios:**

- Collecting operator-level performance data on Ascend NPU
- Profiling model inference performance
- Identifying performance bottlenecks through operator execution
- Comparing operator performance between device and simulator modes
- Generating performance analysis reports for model optimization

**Typical User Phrases:**

- "Profile operator performance on Ascend NPU"
- "Collect performance data using msopprof"
- "Generate performance analysis report"
- "Compare device vs simulator profiling"
- "Identify performance bottlenecks"
- "AscendCollectionOperatorPerformanceData"
- "msopprofPerformance"
- "PerformanceAnalysisReport"

## Scope

**Supported**:

- Operator performance data collection
- Device mode profiling
- Simulator mode profiling
- Report generation

**Not supported**:

- System-level profiling
- Non-Ascend platforms

## Core Workflow

### 1. Profiling Configuration

- Set up profiling parameters
- Configure collection mode (device/simulator)

### 2. Data Collection

- Execute profiling on target model
- Collect operator performance data

### 3. Report Generation

- Generate profiling reports
- Output performance metrics

### 4. Data Export

- Export data to profiling database
- Prepare for further analysis

## Enhanced Features

### Best Practices Knowledge Base

This skill integrates a searchable knowledge base containing migration success
stories and optimization patterns:

**Features:**

- **Case Study Repository**: Searchable database of migration success stories
  for common model architectures
- **Operator Optimization Recipes**: Proven optimization patterns with code
  snippets for common operators
- **Similarity Matching**: Recommends proven solutions based on model
  architecture similarity
- **Performance Patterns**: Collection of known performance patterns and
  anti-patterns
- **Expert Recommendations**: Curated tips from Ascend optimization experts

**Knowledge Base Structure:**

- **Case Studies**: YOLO, ResNet, UNet migration success stories
- **Operator Recipes**: Conv2D, MatMul, Attention optimization patterns
- **Performance Patterns**: Common bottleneck patterns and solutions
- **Expert Tips**: Optimization best practices from field experts

### YOLOv8 Migration Success Story

#### Model Information

- Model: YOLOv8s
- Input: 640x640
- Target: Ascend 910B

#### Challenges Encountered

1. **Issue**: NMS operator fallback to CPU

   - **Solution**: Implemented AscendC NMS operator
   - **Gain**: 30% latency reduction

2. **Issue**: Memory bandwidth bottleneck

   - **Solution**: Optimized data layout and batch processing
   - **Gain**: 15% throughput improvement

3. **Issue**: Custom activation function

   - **Solution**: Replaced with supported operators
   - **Gain**: Stable NPU execution

#### Final Results

- **Latency**: 8.2 ms → 5.1 ms (-37.8%)
- **Throughput**: 122 FPS → 196 FPS (+60.7%)
- **Accuracy**: 60.2% → 60.4% (+0.2%)

#### Key Takeaways

- Always check operator coverage before migration
- Implement custom operators for critical path
- Optimize memory access patterns

### Operator Optimization Recipes

- **Conv2D**: Padding overhead → Use native NPU padding (5-10% gain)
- **MatMul**: Memory layout → Optimal tiling config (10-15% gain)
- **Attention**: FlashAttention → Enable NPU FlashAttention (20-30% gain)
- **NMS**: CPU fallback → AscendC implementation (25-35% gain)

## Reference Documents

- [Acceptance Criteria](references/acceptance-criteria.md) - Functional
  acceptance criteria
- [Verification Method](references/verification-method.md) - Verification approach
- [Troubleshooting](references/troubleshooting.md) - Common issues and solutions

## Prerequisites

- msopprof >= 1.0.0 installed
- CANN >= 7.0.0 installed
- Ascend NPU driver installed
- Operator code to be analyzed

## Core Commands

```bash
# Collect operator performance data
msopprof --output=/path/to/output \
  --mode=device \
  ./my_operator

# Analyze performance report
python3 scripts/analyze_profile.py --data /path/to/output
```

## Parameter Confirmation

- **output**: Performance data output path (Required)
- **mode**: Collection mode (device/simulator) (Optional)
- **operator**: Operator executable file path (Required)
