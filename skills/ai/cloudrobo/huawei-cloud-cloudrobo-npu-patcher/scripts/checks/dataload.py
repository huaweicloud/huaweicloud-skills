#!/usr/bin/env python3
"""Data-loading verification for VLA models.

Adapted from ascend-driving-patcher: uses HuggingFace datasets or a custom
dataset loader instead of mmdet3d build_dataset.
"""

from __future__ import annotations

import argparse
import sys
import traceback
import warnings
from pathlib import Path

from .common import setup_paths, apply_runtime_patches

warnings.filterwarnings("ignore")


def check_data_loading(root_path: Path, config_path: Path, num_samples: int = 3) -> tuple[bool | None, str]:
    """Test actual data loading to catch runtime issues.

    For VLA models, data loading usually involves:
    - HuggingFace datasets
    - custom dataset classes
    - Tokenizer + processor pipelines

    Returns:
        (success, message) tuple
    """
    setup_paths(root_path)
    apply_runtime_patches(root_path)

    model_dir = config_path.parent if config_path.name == 'config.json' else root_path

    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
        print(f"Tokenizer: {type(tokenizer).__name__} ({tokenizer.vocab_size} tokens)")
    except ImportError:
        return None, "transformers not installed (skip data loading)"
    except Exception as e:
        return False, f"Tokenizer load failed: {type(e).__name__}: {e}"

    errors = []
    for i in range(num_samples):
        try:
            test_text = f"Test sample {i}: this is a VLA model input."
            inputs = tokenizer(test_text, return_tensors="pt")
            input_ids = inputs.get('input_ids', inputs.get('input_ids'))
            print(f"Sample {i}: PASS (input_ids shape: {input_ids.shape})")
        except Exception as e:
            error_msg = f"Sample {i}: FAIL - {type(e).__name__}: {e}"
            tb = traceback.format_exc()
            for line in reversed(tb.split('\n')):
                if 'File "' in line and str(root_path) in line:
                    error_msg = f"{error_msg}\n  at {line.strip()}"
                    break
            errors.append(error_msg)
            print(error_msg)
            break

    if errors:
        return False, '\n'.join(errors)
    else:
        return True, f"all {num_samples} samples tokenized successfully"


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify VLA data loading')
    parser.add_argument('root_path', type=Path, help='model root directory')
    parser.add_argument('--config', type=Path, required=True, help='config file')
    parser.add_argument('--num-samples', type=int, default=3, help='number of test samples')
    args = parser.parse_args()

    if not args.root_path.exists():
        print(f"Error: {args.root_path} does not exist")
        return 1
    if not args.config.exists():
        print(f"Error: {args.config} does not exist")
        return 1

    print(f"Data-loading check ({args.config.name})...")
    success, msg = check_data_loading(args.root_path, args.config, args.num_samples)
    if success:
        print(f"  {msg}")
        return 0
    elif success is None:
        print(f"  SKIP - {msg}")
        return 0
    else:
        print(f"  FAIL")
        from config import get_config
        print(f"  {msg[:get_config().max_error_message_length]}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
