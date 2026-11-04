"""NPU runtime patches for VLA models — automatically registered via
build_vla_patcher().

Runtime hooks that transparently handle device mismatches and NPU-specific
behavior for VLA (Vision-Language-Action) models.

Correctness patches (zero-config, always active):
- TensorIndexDevice: auto-aligns integer and boolean index tensors to the
  indexed tensor's device.
- TorchTensorSafe: intercepts torch.tensor() calls to handle 0-dim NPU
  tensor elements crashing under transfer_to_npu's len() check.
- TensorNumpySafe: auto-inserts .cpu() before NPU tensors call .numpy().
- NanToNumSafe: auto-converts half-precision tensors to float32 before
  torch.nan_to_num().
- Float64To32: module-level torch.float64→float32 replacement + copyreg.pickle
  fix + from_numpy/as_tensor/Tensor.to hooks. Prevents DT_DOUBLE from
  reaching the NPU.
- PowFloatSafe: torch.pow with fractional exponents returns float64 on NPU.
  Auto-converts the result to float32.
- SdpaMaskBroadcast: fixes the NPU SDPA mask broadcast error — explicitly
  expands the [B, N, 1, Skv] broadcast mask to [B, N, Sq, Skv].

Performance patches (zero-config, always active):
- BuiltinMinMaxNPU: Python builtin min/max with NPU tensors — redirects
  n-dim tensor pairs to torch.minimum/maximum (stays on NPU, no sync), and
  moves 0-dim tensor pairs to CPU for comparison then back.

Optional patches (off by default, enable explicitly):
- AdamWFused: redirects torch.optim.AdamW to torch_npu.optim.NpuFusedAdamW
  to improve NPU throughput. Cost: the optimizer state is merged into one
  contiguous large tensor, which may OOM with large models / tight memory.
  Enable via: build_vla_patcher(fused_adamw=True).

Patch strategy:
- build_vla_patcher(): applies all runtime patches and returns a context
  manager for the entry point's `with`. No mx_driving dependency.
"""
from __future__ import annotations

import builtins
import copyreg as _copyreg
import importlib
import sys
from contextlib import contextmanager
from typing import List

import torch
import torch.nn.functional as F
import torch_npu


# =============================================================================
# TensorIndexDevice — auto-align index tensors to the indexed tensor's device
# =============================================================================

def _align_index_devices(tensor: torch.Tensor, index: object) -> object:
    if isinstance(index, torch.Tensor):
        if index.dtype == torch.bool or index.dtype in (torch.int8, torch.int16, torch.int32, torch.int64,
                           torch.uint8):
            if index.device != tensor.device:
                return index.to(device=tensor.device)
        return index
    if isinstance(index, tuple):
        return tuple(_align_index_devices(tensor, sub) for sub in index)
    return index


def _wrap_getitem(original):
    def wrapper(self, index):
        index = _align_index_devices(self, index)
        return original(self, index)
    return wrapper


def _wrap_setitem(original):
    def wrapper(self, index, value):
        index = _align_index_devices(self, index)
        return original(self, index, value)
    return wrapper


class TensorIndexDevice:
    name = "tensor_index_device"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        original_getitem = torch.Tensor.__getitem__
        original_setitem = torch.Tensor.__setitem__
        torch.Tensor.__getitem__ = _wrap_getitem(original_getitem)
        torch.Tensor.__setitem__ = _wrap_setitem(original_setitem)
        return []

    @classmethod
    def revert(cls):
        pass


# =============================================================================
# TorchTensorSafe — prevent torch.tensor() 0-dim NPU tensor crashes
# =============================================================================

_original_tensor = None


def _convert_0d_tensors(data):
    """Recursively convert 0-dim NPU tensors in nested lists/tuples to
    Python scalars."""
    if isinstance(data, torch.Tensor) and data.dim() == 0:
        return data.item()
    if isinstance(data, (list, tuple)):
        converted = [_convert_0d_tensors(x) for x in data]
        return type(data)(converted) if isinstance(data, tuple) else converted
    return data


class _Found0d(Exception):
    """Sentinel exception for quickly detecting 0-dim tensors in nested
    structures."""
    pass


def _has_0d_nested(data, _depth=0):
    """Raise _Found0d if a 0-dim tensor exists at any nesting level."""
    if _depth > 10:
        return
    if isinstance(data, torch.Tensor):
        if data.dim() == 0:
            raise _Found0d()
        return
    if isinstance(data, (list, tuple)):
        for x in data:
            _has_0d_nested(x, _depth + 1)


def _safe_tensor(data, *args, **kwargs):
    if _original_tensor is None:
        return torch.tensor(data, *args, **kwargs)
    if isinstance(data, (list, tuple)) and data:
        if all(isinstance(x, torch.Tensor) for x in data):
            return torch.stack(list(data))
        try:
            _has_0d_nested(data)
        except _Found0d:
            converted = _convert_0d_tensors(data)
            return _original_tensor(converted, *args, **kwargs)
    return _original_tensor(data, *args, **kwargs)


def _install_torch_tensor_safe():
    global _original_tensor
    if _original_tensor is not None:
        return
    _original_tensor = torch.tensor
    torch.tensor = _safe_tensor


class TorchTensorSafe:
    name = "torch_tensor_safe"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        _install_torch_tensor_safe()
        return []

    @classmethod
    def revert(cls):
        global _original_tensor
        if _original_tensor is None:
            return
        torch.tensor = _original_tensor
        _original_tensor = None


# =============================================================================
# BuiltinMinMaxNPU — Python min/max with NPU tensors
# =============================================================================

_original_min = builtins.min
_original_max = builtins.max


def _npu_min_max_impl(orig_func, *args, **kwargs):
    if len(args) >= 2:
        a, b = args[0], args[1]
        if (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)
                and a.shape == b.shape
                and (a.is_npu or b.is_npu)):
            if orig_func is _original_min:
                return torch.minimum(a, b)
            else:
                return torch.maximum(a, b)
        if (isinstance(a, torch.Tensor) and a.dim() == 0
                and isinstance(b, torch.Tensor) and b.dim() == 0
                and (a.is_npu or b.is_npu)):
            device = a.device if a.is_npu else b.device
            ca = a.cpu() if a.is_npu else a
            cb = b.cpu() if b.is_npu else b
            result = orig_func(ca, cb, **kwargs)
            return result.to(device) if isinstance(result, torch.Tensor) else result
    return orig_func(*args, **kwargs)


def _npu_aware_min(*args, **kwargs):
    return _npu_min_max_impl(_original_min, *args, **kwargs)


def _npu_aware_max(*args, **kwargs):
    return _npu_min_max_impl(_original_max, *args, **kwargs)


class BuiltinMinMaxNPU:
    name = "builtin_min_max_npu"
    target_module = "builtins"

    @classmethod
    def apply_all(cls, options=None):
        builtins.min = _npu_aware_min
        builtins.max = _npu_aware_max
        return []

    @classmethod
    def revert(cls):
        builtins.min = _original_min
        builtins.max = _original_max


# =============================================================================
# TensorNumpySafe — auto-insert .cpu() before NPU tensors call .numpy()
# =============================================================================

_original_numpy = None


def _safe_numpy(self, *args, **kwargs):
    if self.is_npu:
        return _original_numpy(self.cpu(), *args, **kwargs)
    return _original_numpy(self, *args, **kwargs)


class TensorNumpySafe:
    name = "tensor_numpy_safe"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        global _original_numpy
        if _original_numpy is not None:
            return []
        _original_numpy = torch.Tensor.numpy
        torch.Tensor.numpy = _safe_numpy
        return []

    @classmethod
    def revert(cls):
        global _original_numpy
        if _original_numpy is None:
            return
        torch.Tensor.numpy = _original_numpy
        _original_numpy = None


# =============================================================================
# NanToNumSafe — auto-convert half precision to float32 before torch.nan_to_num
# =============================================================================

_original_nan_to_num = None


def _safe_nan_to_num(input, *args, **kwargs):
    if isinstance(input, torch.Tensor) and input.dtype in (torch.float16, torch.bfloat16):
        return _original_nan_to_num(input.float(), *args, **kwargs)
    return _original_nan_to_num(input, *args, **kwargs)


class NanToNumSafe:
    name = "nan_to_num_safe"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        global _original_nan_to_num
        if _original_nan_to_num is not None:
            return []
        _original_nan_to_num = torch.nan_to_num
        torch.nan_to_num = _safe_nan_to_num
        return []

    @classmethod
    def revert(cls):
        global _original_nan_to_num
        if _original_nan_to_num is None:
            return
        torch.nan_to_num = _original_nan_to_num
        _original_nan_to_num = None


# =============================================================================
# Float64To32 — redirect all float64 paths to float32 (NPU-safe)
# =============================================================================

_orig_float64 = torch.float64
_orig_double = torch.double
_orig_DoubleTensor = torch.DoubleTensor
_orig_tensor_double = torch.Tensor.double
_orig_from_numpy = torch.from_numpy
_orig_as_tensor = torch.as_tensor
_orig_to = torch.Tensor.to


def _pickle_dtype(dtype):
    if dtype is _orig_float64:
        return _unpickle_dtype, ('float32',)
    name = str(dtype).replace('torch.', '')
    return _unpickle_dtype, (name,)


def _unpickle_dtype(name):
    return getattr(torch, name)


def _safe_from_numpy(arr, *args, **kwargs):
    t = _orig_from_numpy(arr, *args, **kwargs)
    if t.dtype == _orig_float64:
        return t.float()
    return t


def _safe_as_tensor(data, *args, **kwargs):
    t = _orig_as_tensor(data, *args, **kwargs)
    if isinstance(t, torch.Tensor) and t.dtype == _orig_float64:
        return t.float()
    return t


def _safe_to(self, *args, **kwargs):
    result = _orig_to(self, *args, **kwargs)
    if isinstance(result, torch.Tensor) and result.dtype == _orig_float64 and result.is_npu:
        return result.float()
    return result


class Float64To32:
    name = "float64_to_32"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        if getattr(cls, '_applied', False):
            return []

        _copyreg.pickle(torch.dtype, _pickle_dtype)

        torch.float64 = torch.float32
        torch.double = torch.float32
        torch.DoubleTensor = torch.FloatTensor
        torch.Tensor.double = torch.Tensor.float

        from torch.storage import _dtype_to_storage_type_map
        _dtype_to_storage_type_map.cache_clear()
        _dtype_to_storage_type_map()[_orig_float64] = 'DoubleStorage'

        torch.from_numpy = _safe_from_numpy
        torch.as_tensor = _safe_as_tensor
        torch.Tensor.to = _safe_to

        cls._applied = True
        return []

    @classmethod
    def revert(cls):
        if not getattr(cls, '_applied', False):
            return
        torch.Tensor.to = _orig_to
        torch.from_numpy = _orig_from_numpy
        torch.as_tensor = _orig_as_tensor
        from torch.storage import _dtype_to_storage_type_map
        _dtype_to_storage_type_map.cache_clear()
        torch.float64 = _orig_float64
        torch.double = _orig_double
        torch.DoubleTensor = _orig_DoubleTensor
        torch.Tensor.double = _orig_tensor_double
        cls._applied = False


# =============================================================================
# PowFloatSafe — auto .float() on torch.pow with fractional exponents
# =============================================================================
#
# NPU's torch.pow with fractional exponents (e.g. 0.5, -0.5) returns
# float64. This patch intercepts torch.pow and auto-converts the result to
# float32 when the exponent is a fractional scalar.

_original_pow = None


def _is_fractional_scalar(value):
    """Check whether a value is fractional (non-integer)."""
    if isinstance(value, (int, float)):
        try:
            return float(value) != int(value)
        except (ValueError, OverflowError):
            return False
    return False


def _safe_pow(input, exponent, *args, **kwargs):
    result = _original_pow(input, exponent, *args, **kwargs)
    if _is_fractional_scalar(exponent):
        if isinstance(result, torch.Tensor) and result.dtype == _orig_float64:
            return result.float()
    return result


class PowFloatSafe:
    name = "pow_float_safe"
    target_module = "torch"

    @classmethod
    def apply_all(cls, options=None):
        global _original_pow
        if _original_pow is not None:
            return []
        _original_pow = torch.pow
        torch.pow = _safe_pow
        return []

    @classmethod
    def revert(cls):
        global _original_pow
        if _original_pow is None:
            return
        torch.pow = _original_pow
        _original_pow = None


# =============================================================================
# AdamWFused — redirect AdamW to NpuFusedAdamW [off by default]
# =============================================================================
#
# Fuses the updates of many parameters into a few large kernels, reducing
# kernel launches and improving NPU throughput.
#
# Cost: the fused implementation merges the optimizer state into one
# contiguous large tensor, which may OOM when memory is tight. Therefore
# this patch is off by default, enabled only explicitly at the entry point:
# build_vla_patcher(fused_adamw=True).

_original_AdamW = None


class AdamWFused:
    name = "adamw_fused"
    target_module = "torch.optim"

    @classmethod
    def apply_all(cls, options=None):
        # Not replaced by default; only enabled when options explicitly
        # request fused_adamw=True
        if not (options or {}).get("fused_adamw", False):
            return []
        global _original_AdamW
        if _original_AdamW is not None:
            return []
        try:
            from torch_npu.optim import NpuFusedAdamW
            _original_AdamW = torch.optim.AdamW
            torch.optim.AdamW = NpuFusedAdamW
        except (ImportError, AttributeError):
            pass
        return []

    @classmethod
    def revert(cls):
        global _original_AdamW
        if _original_AdamW is None:
            return
        torch.optim.AdamW = _original_AdamW
        _original_AdamW = None


# =============================================================================
# SdpaMaskBroadcast — fix the NPU SDPA mask broadcast error
# =============================================================================
#
# Error symptom:
#     aclnnFlashAttentionScore failed, error 561103
#     get unsupported atten_mask shape, the shape is [B, N, 1, Skv]
#     (Sq dimension is 1, indicating broadcast)
#
# Root cause: F.scaled_dot_product_attention is intercepted by torch_npu on
# NPU, which calls aclnnFlashAttentionScore underneath. That operator
# requires the mask's Sq dimension to equal the actual query length, and
# **does not accept the Sq=1 broadcast form**; CUDA's SDPA supports this
# broadcast (implicit copy), so the same code works on GPU but crashes on
# NPU.
#
# Who triggers it (diffusers path):
#   The VLA's DiT diffusion action head uses diffusers' AttnProcessor2_0 for
#   cross-attention. It turns the VLM output's 2D padding mask (B, Skv) into
#   the (B, N, 1, Skv) broadcast form via prepare_attention_mask and view,
#   then passes it to F.scaled_dot_product_attention, triggering the error
#   on NPU.
#
# Who does not trigger it (transformers path):
#   The VLM backbone's mask is managed internally by transformers with the
#   correct format, and does not produce an Sq=1 broadcast. The issue is
#   unrelated to the attn_implementation value.
#
# This patch's trigger conditions (only expands when all are met; otherwise
# passes through unchanged, zero impact):
#   - attn_mask is 4D and shape[2] == 1 (Sq broadcast)
#   - query.shape[2] != 1 (actual query length > 1)
#   - query.device.type == "npu" (NPU only)
#   Never triggers when the mask is None / 2D / 3D / Sq already expanded /
#   non-NPU.
#
# Fix: explicitly expand (B, N, 1, Skv) to (B, N, Sq, Skv), which is
# mathematically equivalent to CUDA's implicit broadcast, zero precision
# impact.

_original_sdpa = None


def _npu_compat_sdpa(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    attn_mask: torch.Tensor | None = None,
    dropout_p: float = 0.0,
    is_causal: bool = False,
    scale: float | None = None,
    **kwargs,
) -> torch.Tensor:
    if (
        attn_mask is not None
        and attn_mask.ndim == 4
        and attn_mask.shape[2] == 1
        and query.shape[2] != 1
        and query.device.type == "npu"
    ):
        attn_mask = attn_mask.expand(-1, -1, query.shape[2], -1).contiguous()

    return _original_sdpa(
        query,
        key,
        value,
        attn_mask=attn_mask,
        dropout_p=dropout_p,
        is_causal=is_causal,
        scale=scale,
        **kwargs,
    )


class SdpaMaskBroadcast:
    name = "sdpa_mask_broadcast"
    target_module = "torch.nn.functional"

    @classmethod
    def apply_all(cls, options=None):
        global _original_sdpa
        if _original_sdpa is not None:
            return []
        _original_sdpa = F.scaled_dot_product_attention
        F.scaled_dot_product_attention = _npu_compat_sdpa
        return []

    @classmethod
    def revert(cls):
        global _original_sdpa
        if _original_sdpa is None:
            return
        F.scaled_dot_product_attention = _original_sdpa
        _original_sdpa = None


# =============================================================================
# Patch strategy — build_vla_patcher()
# =============================================================================

ALL_RUNTIME_PATCHES = [
    Float64To32,
    TensorNumpySafe,
    NanToNumSafe,
    TensorIndexDevice,
    TorchTensorSafe,
    BuiltinMinMaxNPU,
    PowFloatSafe,
    SdpaMaskBroadcast,
]


class _NullPatcher:
    """Null patcher — patches applied directly, no framework dependency.

    Provides apply() and a context-manager interface for code expecting an
    mx_driving-style patcher object.
    """
    def apply(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def build_vla_patcher(fused_adamw: bool = False):
    """Apply all VLA runtime patches and return a context manager.

    Args:
    - fused_adamw (bool, default False): whether to enable the
      NpuFusedAdamW fused optimizer.

    Usage in train.py / inference.py:
        from runtime_patches import build_vla_patcher

        with build_vla_patcher():
            main()
    """
    for patch_cls in ALL_RUNTIME_PATCHES:
        patch_cls.apply_all()
    if fused_adamw:
        AdamWFused.apply_all(options={"fused_adamw": True})

    return _NullPatcher()
