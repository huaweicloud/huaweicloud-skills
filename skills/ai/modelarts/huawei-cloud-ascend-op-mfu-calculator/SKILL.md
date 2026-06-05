---
name: huawei-cloud-ascend-op-mfu-calculator
description: |
  Calculate MFU (Machine FLOP Utilization) for operators like matmul/GEMM/FlashAttention on Ascend NPU, providing clear formulas and derivation process
  Use this skill when the user wants to: (1) calculate MFU for matrix operations, (2) analyze operator performance efficiency, (3) understand hardware utilization, (4) optimize operator implementation
  Trigger: user mentions "MFU", "machine flop utilization", "operator FLOPs", "matmul performance", "GEMM efficiency", "Ascend MFU", "算子MFU", "算力利用率", "矩阵乘效率", "GEMM性能", "FlashAttention性能"
tags: [Ascend, MFU, operator, performance]
compatibility:
  - Python3 >= 3.8
allowed-tools:
  - python3
---

# Huawei Cloud Ascend Operator MFU Calculator

## Overview

This skill calculates MFU (Machine FLOP Utilization) for operators like matmul/GEMM/FlashAttention on Ascend NPU, providing clear formulas and derivation process.

**Architecture**: Input Validation → FLOPs Calculation → Achieved TFLOPs/s → MFU Calculation → Result Analysis

**Related Skills**:
- `huawei-cloud-ascend-profiler-db-explorer` - Profiling data analysis for operator performance data

## Prerequisites

1. Python 3.8+ installed
2. Basic understanding of FLOPs calculation concepts

## Usage Scenarios

**Typical Problem Scenarios**:
- Evaluating how well an operator utilizes Ascend NPU compute power
- Comparing performance of different operator implementations
- Identifying optimization opportunities for matrix operations

**Typical User Utterances**:
- "Calculate MFU for my GEMM operator"
- "What's the machine FLOP utilization for FlashAttention?"
- "Analyze my matmul operator performance efficiency"

## Workflow

1. **Input Collection**: Gather operator parameters (matrix dimensions, data types, execution time)
2. **FLOPs Calculation**: Compute theoretical FLOPs for the operation
3. **Achieved Performance**: Calculate achieved TFLOPs/s from execution time
4. **MFU Calculation**: Apply formula MFU = Achieved FLOPs / Peak FLOPs
5. **Result Analysis**: Provide interpretation and optimization suggestions

## MFU Calculation Formula

MFU = (Achieved FLOPs / Peak FLOPs) × 100%

**Where**:
- Achieved FLOPs = Operation FLOPs / Execution Time
- Peak FLOPs = Hardware-specific peak performance (e.g., Ascend 910B: 256 TFLOPs for FP16)

## Reference Documents

| Document | Description |
| -------- | ----------- |
| [Ascend 910B Series Technical Specifications](https://e.huawei.com/cn/products/computing/ascend-910) | Official Ascend 910B series product specifications |
| [MFU Calculation Methodology](references/mfu-calculation-methodology.md) | Detailed MFU calculation formulas and examples |
| [FlashAttention Technical Paper](https://arxiv.org/abs/2205.14135) | Original FlashAttention research paper |

## Enhanced Features

### Intelligent Bottleneck Diagnoser
- AI-powered bottleneck diagnosis that analyzes profiling data to identify root causes automatically
- Classifies bottlenecks into categories: memory-bound, compute-bound, communication-bound, or operator-fallback
- Provides actionable optimization recommendations with priority ranking
- Includes pattern matching for known performance anti-patterns

## Parameter Confirmation

| Parameter | Description | Required |
|-----------|-------------|----------|
| operator | Operator type (matmul/flash_attention/gemm, etc.) | Yes |
| flops | Theoretical FLOPs of the operator | Yes |
| time_ms | Operator execution time (milliseconds) | Yes |
| peak_tflops | Hardware peak computing power (TFLOPS) | Yes |
| device | NPU device type (910B/910, etc.) | No |
