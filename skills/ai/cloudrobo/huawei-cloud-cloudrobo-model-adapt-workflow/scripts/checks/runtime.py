#!/usr/bin/env python3
"""NPU runtime verification for VLA models.

Adapted from ascend-driving-patcher: removed the mx_driving check, added a
transformers availability check.

Can run standalone:
    python runtime.py
"""

import sys
import warnings

warnings.filterwarnings("ignore", category=ImportWarning)
warnings.filterwarnings("ignore", message=".*transfer_to_npu.*")
warnings.filterwarnings("ignore", message=".*torch.jit.script.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)


def _check_torch_npu_import() -> tuple[str, str]:
    """Test 1: torch_npu import (critical)."""
    try:
        import torch_npu  # noqa: F401
        return ("torch_npu import", "PASS")
    except ImportError as e:
        return ("torch_npu import", f"FAIL: {e}")


def _check_npu_availability() -> tuple[str, str, bool]:
    """Test 2: torch.npu.is_available(). Returns (name, status,
    available)."""
    import torch
    try:
        available = torch.npu.is_available()
        if available:
            device_count = torch.npu.device_count()
            return ("NPU availability", f"PASS ({device_count} devices)", available)
        else:
            return ("NPU availability", "WARNING: no NPU devices detected", available)
    except Exception as e:
        return ("NPU availability", f"ERROR: {e}", False)


def _check_transformers_import() -> tuple[str, str]:
    """Test 3: transformers import (VLA models depend on this library)."""
    try:
        import transformers  # noqa: F401
        return ("transformers import", f"PASS (v{transformers.__version__})")
    except ImportError as e:
        return ("transformers import", f"WARNING: {e}")


def _check_npu_tensor_operation(available: bool) -> tuple[str, str]:
    """Test 4: basic NPU tensor operations."""
    if not available:
        return ("NPU tensor operation", "SKIP (no NPU)")
    try:
        import torch
        x = torch.randn(2, 3).npu()
        y = x + 1
        z = y.cpu()
        return ("NPU tensor operation", "PASS")
    except Exception as e:
        return ("NPU tensor operation", f"FAIL: {e}")


def _check_npu_config_setting() -> tuple[str, str]:
    """Test 5: torch.npu.config.allow_internal_format."""
    try:
        import torch
        torch.npu.config.allow_internal_format = False
        return ("NPU config setting", "PASS")
    except Exception as e:
        return ("NPU config setting", f"WARNING: {e}")


def _check_npu_fusion_attention() -> tuple[str, str]:
    """Test 6: npu_fusion_attention availability (the underlying
    dependency of transformers' built-in NPU flash attention)."""
    try:
        import torch
        import torch_npu
        q = torch.randn(1, 4, 2, 8).npu()
        k = torch.randn(1, 4, 2, 8).npu()
        v = torch.randn(1, 4, 2, 8).npu()
        out = torch_npu.npu_fusion_attention(q, k, v, 2,
                    input_layout="BSND", pre_tockens=65536,
                    next_tockens=65536, scale=0.35,
                    keep_prob=1.0, sync=False, inner_precise=0)[0]
        return ("npu_fusion_attention", "PASS")
    except Exception as e:
        return ("npu_fusion_attention", f"FAIL: {e}")


def _evaluate_results(results: list[tuple[str, str]]) -> bool:
    """Print the results; return True when there are no critical
    failures."""
    has_critical_failure = False
    failed = []

    for name, status in results:
        if "FAIL" in status:
            failed.append(f"{name}: {status}")
            if "torch_npu" in name:
                has_critical_failure = True
        elif "WARNING" in status:
            print(f"  {name}: {status}")

    if failed:
        for f in failed:
            print(f"  {f}")
    elif not has_critical_failure:
        print("  PASS - all runtime checks passed")

    return not has_critical_failure


def check_runtime_npu() -> bool:
    """Check the NPU runtime environment for VLA models.

    Tests:
    1. torch_npu import (critical)
    2. torch.npu.is_available()
    3. transformers import (VLA dependency)
    4. basic NPU tensor operations
    5. torch.npu.config.allow_internal_format
    6. npu_fusion_attention (underlying dependency of transformers'
       built-in NPU flash attention)
    """
    name, status = _check_torch_npu_import()
    if status.startswith("FAIL"):
        print(f"  {name}: {status}")
        return False

    results: list[tuple[str, str]] = [(name, status)]

    name, status, available = _check_npu_availability()
    results.append((name, status))

    results.append(_check_transformers_import())
    results.append(_check_npu_tensor_operation(available))
    results.append(_check_npu_config_setting())
    results.append(_check_npu_fusion_attention())

    return _evaluate_results(results)


def main() -> int:
    print("NPU runtime check (VLA)...")
    success = check_runtime_npu()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
