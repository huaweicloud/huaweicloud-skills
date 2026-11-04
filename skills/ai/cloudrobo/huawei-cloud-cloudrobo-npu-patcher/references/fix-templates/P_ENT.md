# P_ENT: Entry Point NPU Setup (VLA)

## Problem

VLA training/inference entry point scripts need NPU initialization:
import torch_npu + transfer_to_npu, wrap main() with
build_vla_patcher(), and update CUDA env vars/flags to NPU.

## Fix

### Fix 1: Add NPU imports and the patcher (critical: must be at the very top)

**Before:**
```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
```

**After:**
```python
import torch
import torch_npu
from torch_npu.contrib import transfer_to_npu
from runtime_patches import build_vla_patcher

with build_vla_patcher():
    from transformers import AutoModelForCausalLM, AutoTokenizer

torch.npu.config.allow_internal_format = False
```

`allow_internal_format=False` disables the NPU internal tensor format
(NC1HWC0). Safer during initial adaptation.

`build_vla_patcher()` does two things:
1. Applies all runtime patches (Float64To32, TensorNumpySafe, NanToNumSafe,
   TensorIndexDevice, TorchTensorSafe, BuiltinMinMaxNPU, PowFloatSafe,
   AdamWFused)
2. Returns a context manager for use with `with`

### Fix 2: Wrap main()

**Before:**
```python
if __name__ == '__main__':
    main()
```

**After:**
```python
if __name__ == '__main__':
    torch.multiprocessing.set_start_method("fork", force=True)
    with build_vla_patcher():
        main()
```

`force=True` is required because during NPU training `torch_npu` may have
already initialized the multiprocessing start method at import time.

### Fix 3: CUDA environment variables

**Before:**
```python
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
torch.cuda.set_device(0)
```

**After:**
```python
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1"
torch.npu.set_device(0)
```

## Notes

- `runtime_patches.py` is copied to the `migrate_to_cloudrobo/` directory
  by the execution workflow (SKILL.md step 1). train.sh automatically adds
  `migrate_to_cloudrobo/` to `PYTHONPATH`, so
  `from runtime_patches import build_vla_patcher` works directly.
- Only import `transfer_to_npu` in entry point scripts. In model files,
  only add `import torch_npu` when NPU-specific APIs are needed.
- Both `accelerate launch` and `torchrun` work on NPU. Choose per the
  model project's original launch method.
