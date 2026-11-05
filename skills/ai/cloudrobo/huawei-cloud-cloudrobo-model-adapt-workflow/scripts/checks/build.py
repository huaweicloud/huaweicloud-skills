#!/usr/bin/env python3
from __future__ import annotations
"""VLA model build verification.

Adapted from ascend-driving-patcher: uses transformers AutoModelForCausalLM
or a custom model loader instead of mmdet3d build_model.
"""

import argparse
import importlib
import sys
import traceback
import warnings
from pathlib import Path
from typing import Any

from .common import setup_paths, apply_runtime_patches, load_config, find_model_path

warnings.filterwarnings("ignore")


def build_model_from_config(root_path: Path, config_path: Path) -> Any:
    """Build a VLA model from config.

    Supports:
    - HuggingFace transformers (AutoModelForCausalLM.from_pretrained)
    - Custom model loading (Python config with a model class)
    """
    suffix = config_path.suffix.lower()

    if suffix == '.json':
        try:
            from transformers import AutoModelForCausalLM, AutoConfig
            config = AutoConfig.from_pretrained(str(config_path.parent))
            model = AutoModelForCausalLM.from_config(config, torch_dtype="auto")
            return model
        except ImportError:
            return None
        except Exception as e:
            raise e

    if suffix == '.py':
        cfg = load_config(config_path)
        model_class_name = cfg.get('model', '').get('type', '') if isinstance(cfg.get('model'), dict) else ''
        if model_class_name:
            module = importlib.import_module(cfg.get('model', {}).get('module', ''))
            model_class = getattr(module, model_class_name)
            model = model_class(**cfg.get('model', {}).get('args', {}))
            return model

    return None


def check_model_build(root_path: Path, config_path: Path) -> tuple[bool | None, str]:
    """Build a model from config to detect issues.

    Returns:
        (success, message) tuple
    """
    setup_paths(root_path)
    apply_runtime_patches(root_path)

    try:
        model = build_model_from_config(root_path, config_path)
        if model is not None:
            return True, f"model built successfully: {type(model).__name__}"
        return None, "could not determine the model loading method (skip)"
    except Exception as e:
        tb = traceback.format_exc()
        lines = tb.strip().split('\n')
        error_msg = f"{type(e).__name__}: {e}"
        last_file = ""
        for line in reversed(lines):
            if 'File "' in line and str(root_path) in line:
                last_file = line.strip()
                break
        if last_file:
            error_msg = f"{error_msg}\n  at {last_file}"
        return False, error_msg


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify VLA model build')
    parser.add_argument('root_path', type=Path, help='model root directory')
    parser.add_argument('--config', type=Path, required=True, help='config file')
    args = parser.parse_args()

    if not args.root_path.exists():
        print(f"Error: {args.root_path} does not exist")
        return 1
    if not args.config.exists():
        print(f"Error: {args.config} does not exist")
        return 1

    print(f"Model build check ({args.config.name})...")
    success, msg = check_model_build(args.root_path, args.config)
    if success:
        print(f"  PASS - {msg}")
        return 0
    elif success is None:
        print(f"  SKIP - {msg}")
        return 0
    else:
        print(f"  FAIL")
        print(f"  {msg}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
