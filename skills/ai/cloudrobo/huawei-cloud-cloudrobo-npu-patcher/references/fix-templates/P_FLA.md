# P_FLA: Flash Attention → npu_fusion_attention

## Problem

The flash_attn package is a CUDA-only library and cannot be installed or
imported on NPU. `from flash_attn import ...` crashes directly at import
time; runtime patches cannot intercept it.

## Fix

### Fix 1: Remove flash_attn imports

`flash_attn` imports crash at import time — runtime patches cannot
intercept them. They must be removed from the source.

**Before:**
```python
try:
    from flash_attn.flash_attn_interface import flash_attn_unpadded_kvpacked_func
except:
    from flash_attn.flash_attn_interface import flash_attn_varlen_kvpacked_func as flash_attn_unpadded_kvpacked_func
from flash_attn.bert_padding import unpad_input, pad_input, index_first_axis
```

**After:**
```python
import torch_npu
# remove all flash_attn imports
```

### Fix 2: transformers >= 4.57 + flash_attention_2 → keep on NPU

VLA models usually use HuggingFace transformers' `AutoModel` API.
transformers 4.57+ has built-in NPU flash attention support. When
`attn_implementation="flash_attention_2"` is set, transformers detects the
NPU internally and automatically uses the built-in `npu_flash_attn_func`
(built on `npu_fusion_attention`). No flash_attn package install needed.

If the model code already wraps flash_attn imports in try/except, modify
the except branch:

```python
# before
try:
    import flash_attn
    attn_implementation = "flash_attention_2"
except ImportError:
    attn_implementation = "sdpa"

# after
try:
    import flash_attn
    attn_implementation = "flash_attention_2"
except ImportError:
    if torch.npu.is_available():
        attn_implementation = "flash_attention_2"
    else:
        attn_implementation = "sdpa"
```

### Fix 3: transformers < 4.57 + flash_attention_2 → use sdpa on NPU

transformers < 4.57 cannot load any flash attention function with
`attn_implementation="flash_attention_2"` on npu; it errors out directly.

**Fix: change `flash_attention_2` to `sdpa`.**

**Before:**
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="npu:0",
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)
```

**After:**
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="npu:0",
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",
)
```

**Note**: sdpa performance on NPU depends on the scenario:
- `is_causal=True` (decoder autoregression) → can use the FlashAttentionScore
  fused kernel, good performance
- `is_causal=False` + boolean mask → fused kernel available, good performance
- `is_causal=False` + non-boolean mask → falls back to small-operator
  concatenation, poor performance

### Source That Should NOT Be Modified

`transfer_to_npu` automatically redirects `cuda→npu`. Do not modify:
- `device_map="auto"` → change to `"npu:0"` (covered by Fix 2)
- `torch_dtype` stays unchanged

## Notes

- eager/sdpa attention needs no modification; it works on NPU
- If the model code imports flash_attn functions directly (non-transformers
  path), after removing the imports you need to manually replace them with
  `npu_fusion_attention`
