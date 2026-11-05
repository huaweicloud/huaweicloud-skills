"""Standalone check scripts for VLA verify.py.

Adapted from ascend-driving-patcher: removed the mmcv/mmdet3d-specific
checks, added VLA-specific checks (transformers, tokenizer, data
pipeline).
"""

from .runtime import check_runtime_npu
from .build import check_model_build
from .common import setup_paths, apply_runtime_patches, check_shell_scripts, check_syntax
from .dataload import check_data_loading
from .pipeline import validate_pipeline

__all__ = [
    'check_runtime_npu',
    'check_model_build',
    'check_data_loading',
    'validate_pipeline',
    'setup_paths',
    'apply_runtime_patches',
    'check_shell_scripts',
    'check_syntax',
]
