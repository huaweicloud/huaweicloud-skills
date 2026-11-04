#!/usr/bin/env python3
"""Pipeline verification for VLA models.

Adapted from ascend-driving-patcher: checks tokenizer and data-transform
availability instead of the mmcv dataset/pipeline registry.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

from .common import setup_paths, apply_runtime_patches, load_config

warnings.filterwarnings("ignore")


def _check_tokenizer(root_path: Path, config_path: Path) -> tuple[bool, str]:
    """Check whether the tokenizer can be loaded."""
    model_dir = config_path.parent if config_path.name == 'config.json' else root_path

    tokenizer_files = list(model_dir.glob('tokenizer*.json')) + \
                      list(model_dir.glob('tokenizer_config.json')) + \
                      list(model_dir.glob('vocab.*'))

    if not tokenizer_files:
        return True, "no tokenizer files found (may use custom tokenization)"

    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
        return True, f"Tokenizer: {type(tokenizer).__name__} (vocab_size={tokenizer.vocab_size})"
    except ImportError:
        return True, "transformers not installed (skip tokenizer check)"
    except Exception as e:
        return False, f"Tokenizer load failed: {type(e).__name__}: {e}"


def _check_processor(root_path: Path, config_path: Path) -> tuple[bool, str]:
    """Check whether the processor (image processor + tokenizer) can be
    loaded."""
    model_dir = config_path.parent if config_path.name == 'config.json' else root_path

    try:
        from transformers import AutoProcessor
        processor = AutoProcessor.from_pretrained(str(model_dir), trust_remote_code=True)
        return True, f"Processor: {type(processor).__name__}"
    except ImportError:
        return True, "transformers not installed (skip processor check)"
    except Exception:
        return True, "no processor found (may use custom preprocessing)"


def validate_pipeline(root_path: Path, config_path: Path) -> tuple[bool | None, str]:
    """Validate the VLA data pipeline (without loading real data).

    Checks:
    - Tokenizer availability
    - Processor availability (multimodal models)
    """
    setup_paths(root_path)
    apply_runtime_patches(root_path)

    errors: list[str] = []
    passed: list[str] = []

    tok_ok, tok_msg = _check_tokenizer(root_path, config_path)
    if tok_ok:
        passed.append(tok_msg)
    else:
        errors.append(tok_msg)

    proc_ok, proc_msg = _check_processor(root_path, config_path)
    if proc_ok:
        passed.append(proc_msg)
    else:
        errors.append(proc_msg)

    if errors:
        for e in errors:
            print(f"  FAIL - {e}")
        return False, '\n'.join(errors)

    for p in passed:
        print(f"  PASS - {p}")
    return True, "pipeline verification passed"


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify VLA pipeline')
    parser.add_argument('root_path', type=Path, help='model root directory')
    parser.add_argument('--config', type=Path, required=True, help='config file')
    args = parser.parse_args()

    if not args.root_path.exists():
        print(f"Error: {args.root_path} does not exist")
        return 1
    if not args.config.exists():
        print(f"Error: {args.config} does not exist")
        return 1

    print(f"Pipeline verification ({args.config.name})...")
    success, msg = validate_pipeline(args.root_path, args.config)
    if success:
        print(f"  PASS - {msg}")
        return 0
    else:
        print(f"  FAIL")
        print(f"  {msg}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
