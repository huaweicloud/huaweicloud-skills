# P_RND: Random Tensor Device Mismatch

## Problem

`torch.rand()`, `torch.randn()`, etc. create tensors on CPU by default,
causing unnecessary device transfers.

## Fix

### Fix 1: Create and transfer separately

**Before:**
```python
mask = torch.rand(shape)
mask = mask.to(device)
```

**After:**
```python
mask = torch.rand(shape, device=device)
```

### Fix 2: Chaining with dtype

**Before:**
```python
mask = torch.rand(shape, dtype=dtype).to(device)
```

**After:**
```python
mask = torch.rand(shape, dtype=dtype, device=device)
```

## Notes

- Applies to all random generators: `torch.rand`, `torch.randn`,
  `torch.randint`, `torch.randperm`, etc.
- When both `dtype` and `device` are needed, pass them as constructor
  arguments instead of chaining `.to()`.
