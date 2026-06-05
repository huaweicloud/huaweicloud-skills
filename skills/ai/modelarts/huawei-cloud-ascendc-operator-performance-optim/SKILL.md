---
name: huawei-cloud-ascendc-operator-performance-optim
version: 1.0.0
description: |
  Develop and optimize custom operators using AscendC programming language. Analyze operator performance bottlenecks and conduct optimization validation. Based on AscendC and CANN toolkit
  Use this skill when the user wants to: (1) optimize performance-critical operators on Ascend NPU, (2) develop custom operators for specific workloads, (3) improve model inference performance through operator optimization
  Trigger: user mentions "AscendC", "operator optimization", "custom operator", "performance", "NPU optimization", "Ascend operator", "算子优化", "自定义算子", "算子开发", "AscendC算子", "性能优化"
compatibility:
  - CANN >= 7.0.0
  - AscendC >= 1.0.0
tags: [Ascend, AscendC, operator, optimization]
allowed-tools:
  - python3
  - bash
  - ascendc
---

# Huawei Cloud AscendC Operator Performance Optimization

## Overview

This skill provides guidance for developing and optimizing custom operators using AscendC programming language.

**Architecture**: Performance Analysis → Bottleneck Identification → Operator Development → Optimization → Validation

**Related Skills**:
- `huawei-cloud-ascend-profiler-db-explorer` - Performance data analysis and bottleneck identification
- `huawei-cloud-ascend-small-model-migrate` - Migration workflow that may require operator optimization

## Architecture Components

This skill involves the following cloud services and components:
- **AscendC**: Programming language for custom operator development
- **CANN**: Huawei Cloud AI Computing Platform for NPU
- **Ascend 910B**: Target NPU hardware for operator deployment
- **Ascend Profiler**: Performance analysis tool for validation

**Architecture Diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│            AscendC Operator Optimization Skill             │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Performance │───▶│  Bottleneck  │───▶│  Operator    │ │
│  │  Analysis    │    │  Identification│   │  Development │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Profiling   │    │  Optimization│    │  Validation │ │
│  │  Data        │    │  Techniques  │    │  & Testing  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Use Cases

**Typical Problem Scenarios:**
- Optimizing performance-critical operators on Ascend NPU
- Developing custom operators for specific workloads
- Improving model inference performance through operator optimization
- Fixing operator bottlenecks identified during profiling
- Implementing missing operators for NPU deployment

**Typical User Phrases:**
- "Optimize my custom operator for Ascend"
- "Develop AscendC operator for GEMM"
- "Improve inference performance on NPU"
- "Fix bottleneck operator"
- "Implement custom operator using AscendC"
- "AscendCOperator"
- "OptimizationAscendOperatorPerformance"
- "OperatorPerformance"

## Scope

**Supported**:
- Custom operator development in AscendC
- Performance optimization for existing operators
- Operator validation and testing

**Not supported**:
- Non-AscendC operator development
- Framework-level optimizations

## Core Workflow

### 1. Performance Analysis
- Use profiling tools to identify performance bottlenecks
- Analyze operator execution time and resource utilization

### 2. Bottleneck Identification
- Identify operators with high execution time
- Determine optimization opportunities

### 3. Operator Development
- Implement custom operators using AscendC
- Follow AscendC best practices

### 4. Optimization Techniques
- Memory optimization
- Compute optimization
- Data layout optimization

### 5. Validation
- Verify functional correctness
- Validate performance improvement

## Reference Documents

| Document | Description |
|----------|-------------|
| [Acceptance Criteria](references/acceptance-criteria.md) | Functional acceptance criteria |
| [Verification Method](references/verification-method.md) | Verification approach |
| [Troubleshooting](references/troubleshooting.md) | Common issues and solutions |

## Prerequisites

- CANN >= 7.0.0 installed
- AscendC >= 1.0.0 installed
- Ascend NPU driver installed and working properly
- Operator code or performance data to be optimized

## Core Commands

```bash
# Analyze operator performance bottlenecks
msprof --output=/path/to/output ./my_operator

# Optimize operator using AscendC
# Refer to CANN development guide for operator development
```

## Parameter Confirmation

| Parameter | Description | Required |
|-----------|-------------|----------|
| Operator code path | Operator source code to be optimized | Yes |
| Output directory | Performance analysis result output path | Yes |
| Optimization strategy | Performance optimization scheme selection | No |

## Output Format

Performance analysis results are saved in the specified output directory:

```
output/
├── summary.json           # Performance summary
├── operator_stats.csv     # Operator execution statistics
├── timeline.json          # Execution timeline data
└── recommendations.md     # Optimization recommendations
```

**Summary JSON Structure:**
```json
{
  "total_time_ms": 1234.56,
  "operator_count": 42,
  "top_operators": [
    {"name": "CustomGEMM", "time_ms": 456.78, "percentage": 37.0},
    {"name": "VectorAdd", "time_ms": 123.45, "percentage": 10.0}
  ],
  "optimization_candidates": ["CustomGEMM", "DataTransfer"]
}
```

## Validation Method

### Functional Validation
1. Run operator with test inputs
2. Compare outputs with reference implementation
3. Verify numerical accuracy (tolerance: 1e-5 for FP32, 1e-3 for FP16)

### Performance Validation
1. Benchmark operator before optimization
2. Apply optimization changes
3. Benchmark operator after optimization
4. Calculate speedup ratio: `speedup = time_before / time_after`

### Acceptance Criteria
- Functional correctness: Output matches reference within tolerance
- Performance improvement: Speedup >= 1.2x (20% improvement)
- No regression: Other operators not affected

## Best Practices

### Memory Optimization
- Use GM (Global Memory) for large tensors
- Use L1/L0A/L0B for intermediate results in matrix operations
- Align memory access to 32-byte boundaries
- Reuse memory buffers when possible

### Compute Optimization
- Vectorize operations using AscendC intrinsics
- Use MMA (Matrix Multiply Accumulate) for matrix operations
- Parallelize independent operations
- Minimize synchronization points

### Data Layout Optimization
- Use NZ format for matrix operations
- Use ND format for vector operations
- Avoid unnecessary format conversions
- Consider memory coalescing for data access

### Code Structure
- Separate compute logic from memory operations
- Use template metaprogramming for flexibility
- Document optimization assumptions
- Profile before and after each optimization

## Notes

### Common Pitfalls
- **Memory bank conflicts**: Ensure data is distributed across memory banks
- **Unaligned access**: Check 32-byte alignment for all buffers
- **Excessive synchronization**: Minimize barrier usage between kernels
- **Wrong data format**: Match format to operation type (NZ for matmul, ND for vector)

### Performance Tips
1. Profile first to identify real bottlenecks
2. Focus on hot paths (operators with >10% total time)
3. Consider algorithmic changes before micro-optimizations
4. Test with realistic input sizes
5. Validate correctness after each optimization

### Debugging Tips
- Use `ASCENDC_DEBUG=1` for verbose logging
- Check CANN log files in `/var/log/npu/`
- Compare with CPU reference implementation
- Use `msprof` for detailed performance breakdown

### Limitations
- AscendC operators are hardware-specific (910B)
- Not all PyTorch operators have AscendC equivalents
- Custom operators require CANN recompilation for deployment
