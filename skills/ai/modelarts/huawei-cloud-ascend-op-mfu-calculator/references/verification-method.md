# Verification Method

Verify MFU (Machine FLOP Utilization) calculation.

## MFU Definition

$$
MFU = \frac{Achieved\ FLOPs/s}{Peak\ FLOPs/s} = \frac{Actual\ FLOPs}{Peak\ FLOPs \times Time}
$$

## Peak FLOPS Reference

| Chip | FP16/BF16 Peak |
|------|----------------|
| Ascend 910B1 | 378.88 TFLOPS/s |
| Ascend 910B2 | 353.89 TFLOPS/s |
| Ascend 910B3 | 294.91 TFLOPS/s |
| Ascend 910B4 | 270.00 TFLOPS/s |

## FLOPs Calculation

### Matmul/GEMM: (M, K) x (K, N) -> (M, N)

$$
FLOPs = 2 \times M \times K \times N
$$

### Example Calculation

For matmul (1024, 1024) x (1024, 1024):
- FLOPs = 2 x 1024 x 1024 x 1024 = 2,147,483,648
- If execution time = 1ms
- Achieved = 2.15 TFLOPS/s
- MFU on 910B3 = 2.15 / 294.91 = 0.73% (per chip)

## Verification Steps

### 1. Get Operator Dimensions

```python
# From profiling data or model definition
M, K, N = 1024, 1024, 1024
```

### 2. Calculate FLOPs

```python
flops = 2 * M * K * N
print(f"FLOPs: {flops:,}")
```

### 3. Get Execution Time

```python
# From profiling data
import pandas as pd
df = pd.read_csv("OpBasicInfo.csv")
exec_time_us = df[df["Op Name"] == "matmul"]["Task Duration(us)"].values[0]
exec_time_s = exec_time_us * 1e-6
```

### 4. Calculate MFU

```python
achieved_tflops = flops / exec_time_s / 1e12
peak_tflops = 294.91  # 910B3
mfu = achieved_tflops / peak_tflops
print(f"MFU: {mfu:.2%}")
```

## Acceptance Criteria

| Check Item | Expected Result |
|------------|-----------------|
| Dimensions | Correct |
| FLOPs formula | Applied correctly |
| Execution time | From profiling |
| Peak FLOPS | Correct chip model |
| MFU | 0% - 100% |

## Common Issues

### 1. MFU > 100%

**Cause**: Wrong peak FLOPS or dimension error

**Solution**: Verify chip model and dimensions

### 2. Very Low MFU

**Possible Causes**:
- Memory-bound operation
- Small matrix size
- Suboptimal kernel

### 3. Negative MFU

**Cause**: Calculation error

**Solution**: Check all values are positive
