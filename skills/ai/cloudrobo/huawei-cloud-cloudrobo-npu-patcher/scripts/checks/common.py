"""Common utilities for VLA verification checks.

Adapted from ascend-driving-patcher: removed the mmcv/mmdet3d dependency,
uses transformers/JSON config loading and build_vla_patcher().
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=ImportWarning)
warnings.filterwarnings("ignore", message=".*transfer_to_npu.*")
warnings.filterwarnings("ignore", message=".*torch.jit.script.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)


def setup_paths(root_path: Path) -> list[str]:
    """Set up sys.path for model imports. Returns the list of added
    paths."""
    added = [str(root_path)]
    sys.path.insert(0, str(root_path))

    src_path = root_path / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        added.append(str(src_path))

    return added


def apply_runtime_patches(root_path: Path) -> list[str]:
    """Apply runtime_patches.py from the project root (VLA patcher
    convention).

    Uses build_vla_patcher() to apply all VLA runtime patches
    (6 core + 2 VLA-specific). No mx_driving dependency.

    Returns the list of applied patch names, or an empty list.
    """
    if not (root_path / "runtime_patches.py").exists():
        return []

    try:
        import torch_npu
        from torch_npu.contrib import transfer_to_npu
    except ImportError:
        return []

    try:
        rp_module = importlib.import_module("runtime_patches")
    except ImportError:
        return []

    build_patcher = getattr(rp_module, "build_vla_patcher", None)
    if build_patcher is None:
        return []

    try:
        patcher = build_patcher()
        patcher.apply()
        class_patches = getattr(rp_module, "ALL_RUNTIME_PATCHES", [])
        names = [p.__name__ for p in class_patches]
        return names
    except Exception as e:
        print(f"  runtime patch application failed: {type(e).__name__}: {e}", file=sys.stderr)
        return []


def load_config(config_path: Path) -> Any:
    """Load a VLA model config.

    Supports:
    - JSON config files (HuggingFace format)
    - YAML config files
    - Python config files (custom training config)
    """
    suffix = config_path.suffix.lower()

    if suffix == '.json':
        import json
        with open(config_path) as f:
            return json.load(f)

    if suffix in ('.yaml', '.yml'):
        try:
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError("YAML config files require PyYAML")

    if suffix == '.py':
        spec = importlib.util.spec_from_file_location("vla_config", config_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return {k: v for k, v in vars(module).items() if not k.startswith('_')}

    raise ValueError(f"unsupported config format: {suffix}")


def find_model_path(root_path: Path) -> Path | None:
    """Find the model directory containing config.json or model weights.

    VLA models usually have:
    - config.json (HuggingFace format)
    - model weights (.bin, .safetensors)
    - tokenizer files
    """
    for pattern in ['**/config.json', 'config.json']:
        configs = list(root_path.glob(pattern))
        if configs:
            return configs[0].parent

    for pattern in ['**/*.safetensors', '**/*.bin', '*.safetensors', '*.bin']:
        weights = list(root_path.glob(pattern))
        if weights:
            return weights[0].parent

    return None


def check_shell_scripts(root_path: Path) -> list[str]:
    """Scan shell scripts for GPU-specific patterns that need NPU
    adaptation.

    Returns:
        A list of warning strings. An empty list means no issues found.
    """
    from utils import collect_sh_files

    warnings_list = []

    sh_files = collect_sh_files(root_path)
    if not sh_files:
        return []

    for sh_file in sh_files:
        try:
            content = sh_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            logger.warning("read file error")
            continue

        rel_path = sh_file.relative_to(root_path)

        if re.search(r'torch\.distributed\.launch', content):
            warnings_list.append(
                f"{rel_path}: uses 'torch.distributed.launch' — "
                f"change to 'torchrun' to avoid the --local-rank argparse "
                f"issue in PyTorch 2.1+"
            )

        if re.search(r'CUDA_VISIBLE_DEVICES', content):
            warnings_list.append(
                f"{rel_path}: uses 'CUDA_VISIBLE_DEVICES' — "
                f"change to 'ASCEND_RT_VISIBLE_DEVICES' for NPU device selection"
            )

    return warnings_list


def check_syntax(py_files: list[Path]) -> list[tuple[str, str]]:
    """Check the Python syntax of all files with in-process
    py_compile."""
    import py_compile
    errors = []
    for f in py_files:
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((str(f), str(e)))
    return errors
