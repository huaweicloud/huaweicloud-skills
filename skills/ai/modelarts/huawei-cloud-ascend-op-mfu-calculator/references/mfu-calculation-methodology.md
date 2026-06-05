# MFU Calculation Methodology

## Overview

This document provides detailed methodology for calculating Machine FLOP Utilization (MFU) for operators on Ascend NPU. MFU is a key metric to evaluate how effectively an operator utilizes the hardware computing power.

## 1. MFU Definition

Machine FLOP Utilization (MFU) is defined as:

$$
\text{MFU} = \frac{\text{Achieved FLOPs}}{\text{Peak FLOPs}} = \frac{\text{Actual FLOPs produced in computation}}{\text{Theoretical FLOPs executable by hardware in the same time}}
$$

### Unit Conventions

- **FLOPs**: Number of floating-point operations
- **TFLOPs/s**: Trillions of floating-point operations per second
- **Execution Time**: Typically in milliseconds (ms)

### Conversion Factors

```
Achieved FLOPs/s = FLOPs / Execution Time (seconds)
Achieved TFLOPs/s = Achieved FLOPs/s ÷ 1e12
MFU = Achieved TFLOPs/s ÷ Peak TFLOPs/s
```

## 2. Peak FLOPs Reference

### Ascend 910B Series

| Model | FP16/BF16 Peak (TFLOPs/s) |
|-------|---------------------------|
| 910B1 | ≈ 378.88                  |
| 910B2 | ≈ 353.89                  |
| 910B3 | ≈ 294.91                  |
| 910B4 | ≈ 270                     |

## 3. FLOPs Calculation Formulas

### 3.1 Matmul / GEMM

**Standard Matrix Multiplication (M, K) × (K, N):**

$$
\text{FLOPs} \approx 2 \times M \times N \times K
$$

**Batched Matmul (B, M, K) × (B, K, N):**

$$
\text{FLOPs} \approx 2 \times B \times M \times N \times K
$$

### 3.2 Linear Layer

Input: $(B, L, D_\text{in})$, Weight: $(D_\text{in}, D_\text{out})$

$$
\text{FLOPs} \approx 2 \times B \times L \times D_\text{in} \times D_\text{out}
$$

### 3.3 Attention QK^T

$Q=(B, H, L_q, D_h),\ K=(B, H, L_k, D_h)$

$$
\text{FLOPs} \approx 2 \times B \times H \times L_q \times L_k \times D_h
$$

### 3.4 FlashAttention

#### Common Layout (BNSD/BSND/BSH/SBH)

$$
\text{full_attention} = 2 \times q_b \times q_n \times q_s \times k_s \times (q_d + k_d)
$$

**Adjustment based on sparse_mode:**
- sparse_mode == 0: $\text{FLOPs} = \text{full_attention}$
- sparse_mode == 2 or 3 with $q_s == k_s$: $\text{FLOPs} = \text{full_attention} \times 0.5$

#### TND Layout

$$
\text{FLOPs} = 2 \times N \times (D_q + D_k) \times \sum_{i} \text{q_lens}[i] \times \text{kv_lens}[i]
$$

## 4. Step-by-Step Calculation Guide

### Step 1: Gather Input Information

Collect the following from user or profiler:
- Operator type (matmul, GEMM, FlashAttention, etc.)
- Tensor dimensions (batch, sequence length, hidden dimension, etc.)
- Execution time (in milliseconds)
- Hardware peak FLOPs (from table above)

### Step 2: Calculate Operator FLOPs

Use the appropriate formula based on operator type:

```python
# Example: Matmul FLOPs calculation
def calculate_matmul_flops(M, N, K, batch=1):
    return 2 * batch * M * N * K
```

### Step 3: Compute Achieved FLOPs/s

```python
def calculate_achieved_tflops(flops, time_ms):
    time_s = time_ms / 1000
    flops_per_sec = flops / time_s
    tflops_per_sec = flops_per_sec / 1e12
    return tflops_per_sec
```

### Step 4: Calculate MFU

```python
def calculate_mfu(achieved_tflops, peak_tflops):
    return achieved_tflops / peak_tflops
```

## 5. Worked Examples

### Example 1: Simple Matmul

**Input:**
- Matrix A: (1024, 512)
- Matrix B: (512, 1024)
- Execution time: 0.1 ms
- Hardware: Ascend 910B1 (378.88 TFLOPs/s)

**Calculation:**
1. FLOPs = 2 × 1024 × 1024 × 512 = 1,073,741,824
2. Achieved TFLOPs/s = 1,073,741,824 / 0.0001 / 1e12 = 10.74 TFLOPs/s
3. MFU = 10.74 / 378.88 ≈ 0.0283 → 2.83%

### Example 2: Batched Matmul

**Input:**
- Batch size: 32
- Input shape: (32, 64, 128)
- Weight shape: (32, 128, 256)
- Execution time: 0.5 ms
- Hardware: Ascend 910B1 (378.88 TFLOPs/s)

**Calculation:**
1. FLOPs = 2 × 32 × 64 × 256 × 128 = 134,217,728 × 32 = 4,294,967,296
2. Achieved TFLOPs/s = 4,294,967,296 / 0.0005 / 1e12 = 8.59 TFLOPs/s
3. MFU = 8.59 / 378.88 ≈ 0.0227 → 2.27%

### Example 3: Attention QK^T

**Input:**
- Batch: 4
- Heads: 12
- Query length: 1024
- Key length: 1024
- Head dimension: 64
- Execution time: 0.2 ms
- Hardware: Ascend 910B1 (378.88 TFLOPs/s)

**Calculation:**
1. FLOPs = 2 × 4 × 12 × 1024 × 1024 × 64 = 6,442,450,944
2. Achieved TFLOPs/s = 6,442,450,944 / 0.0002 / 1e12 = 32.21 TFLOPs/s
3. MFU = 32.21 / 378.88 ≈ 0.0850 → 8.50%

## 6. Interpretation Guidelines

| MFU Range | Assessment | Possible Causes |
|-----------|------------|-----------------|
| < 20% | Low utilization | Memory bandwidth bottleneck, launch overhead, irregular shapes |
| 20% - 40% | Below average | Suboptimal operator configuration |
| 40% - 60% | Medium | Typical for many workloads |
| 60% - 80% | Good | Well-optimized implementation |
| > 80% | Excellent | Near-optimal utilization |

## 7. Common Pitfalls

### 7.1 Unit Mismatch

**Problem:** Mixing milliseconds and seconds in calculations.

**Solution:** Always convert time to seconds before calculating FLOPs/s.

```python
# Correct
time_s = time_ms / 1000

# Incorrect
# flops_per_sec = flops / time_ms  # Wrong units!
```

### 7.2 Missing Batch Dimension

**Problem:** Forgetting to multiply by batch size.

**Solution:** Always include batch dimension in FLOPs calculation.

### 7.3 Incorrect Peak FLOPs

**Problem:** Using wrong peak FLOPs for the hardware.

**Solution:** Verify the correct model and precision mode with the user.

### 7.4 Ignoring Sparse Mode

**Problem:** Not adjusting for causal mask or sparse attention.

**Solution:** Apply sparse_mode adjustment factors for FlashAttention.

## 8. Troubleshooting Low MFU

### Checklist for Investigation

1. **Check operator dimensions** - Are they optimal for the hardware?
2. **Verify execution time** - Is it accurate from profiler?
3. **Check memory bandwidth** - Is the operator memory-bound?
4. **Review operator configuration** - Are tiling parameters optimal?
5. **Consider fusion** - Can multiple operators be fused?
6. **Check parallelism** - Is the computation properly parallelized?

### Optimization Recommendations

- Increase batch size if memory allows
- Optimize tensor layouts for better memory access
- Use hardware-specific optimizations (e.g., Tensor Core)
- Consider operator fusion to reduce overhead
- Adjust tiling parameters for better cache utilization

## 9. Best Practices

1. **Always verify peak FLOPs** - Confirm with official documentation
2. **Use profiler data** - Get accurate execution times from profiling
3. **Document assumptions** - Note when using approximate values
4. **Include uncertainty** - Mention if results are estimates
5. **Compare with baseline** - Track improvements over time
6. **Consider end-to-end** - MFU is one metric; consider overall performance

## 10. References

- [Ascend 910B Series Technical Specifications](https://e.huawei.com/cn/products/computing/ascend-910)
- [FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)
- [GEMM Performance Optimization Guide](https://developer.nvidia.com/cuda-gemm-performance)
