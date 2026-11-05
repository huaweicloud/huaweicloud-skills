#!/usr/bin/env python3
from __future__ import annotations
"""
Post-patch compilation verification for VLA NPU.

Adapted from ascend-driving-patcher: uses transformers/JSON config
auto-detection instead of mmcv config patterns.

Usage:
    python verify.py /path/to/model [options]
    python verify.py --runtime --pipeline /path/to/model --config config.json

Options:
    --config       config file (auto-detected if not specified)
    --runtime      enable NPU runtime checks
    --pipeline     enable pipeline verification (tokenizer/processor)
    --data         enable real data-loading checks (requires data files)

Check order:
    1. Code integrity — Python syntax + shell script checks
    2. Model build — build the model from config
    3. NPU runtime — NPU imports and basic operations
    4. Pipeline verification — tokenizer/processor checks
    5. Data loading — real data-loading verification
"""

import argparse
import io
import sys
import warnings
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

warnings.filterwarnings("ignore")

from config import get_config
from utils import collect_py_files
from checks import (check_runtime_npu, check_model_build, check_data_loading,
                    validate_pipeline, check_shell_scripts,
                    check_syntax)


def print_result(success: bool | None, msg: str, max_len: int | None = None) -> bool | None:
    if max_len is None:
        max_len = get_config().max_error_message_length

    if success is True:
        print(f"  PASS - {msg.strip()}")
        return True
    elif success is None:
        print(f"  SKIP - {msg.strip()}")
        return None
    else:
        print(f"  FAIL")
        print(f"  {msg.strip()[:max_len]}")
        return False


def _check_code_integrity(py_files, model_path, total_errors):
    print(f"Checking {len(py_files)} Python files...\n")
    print("[1/5] Code integrity...")

    syntax_errors = check_syntax(py_files)
    if syntax_errors:
        cfg = get_config()
        print(f"  Syntax: {len(syntax_errors)} error(s) found:")
        for f, err in syntax_errors[:cfg.max_syntax_errors_shown]:
            print(f"    {f}: {err[:cfg.code_snippet_length]}")
        total_errors += len(syntax_errors)
    else:
        print("  Syntax: PASS")

    sh_warnings = check_shell_scripts(model_path)
    if sh_warnings:
        for w in sh_warnings:
            print(f"  Shell: WARNING: {w}")
    else:
        print("  Shell scripts: PASS")

    return total_errors


def _check_model_build(args, found_config, total_errors):
    if args.config:
        print(f"\n[2/5] Model build ({args.config.name})...")
        build_ok, build_msg = check_model_build(args.path, args.config)
        if not print_result(build_ok, build_msg):
            total_errors += 1
    elif found_config:
        print(f"\n[2/5] Model build (auto-detected: {found_config.name})...")
        build_ok, build_msg = check_model_build(args.path, found_config)
        if not print_result(build_ok, build_msg):
            total_errors += 1
    else:
        print("\n[2/5] Model build... SKIP (no config found, use --config to specify)")

    return total_errors


def _find_config(args, cfg):
    """Auto-detect the config file for VLA models."""
    for pattern in cfg.config_search_patterns:
        configs = list(args.path.glob(pattern))
        if configs:
            return configs[0]
    return None


def _check_runtime(args, total_errors):
    if args.runtime:
        print("\n[3/5] NPU runtime check...")
        success = check_runtime_npu()
        if not success:
            total_errors += 1
    else:
        print("\n[3/5] NPU runtime check... SKIP (use --runtime to enable)")

    return total_errors


def _check_pipeline(args, config_for_checks, cfg, total_errors):
    if args.pipeline:
        if config_for_checks:
            print(f"\n[4/5] Pipeline verification ({config_for_checks.name})...")
            success, msg = validate_pipeline(args.path, config_for_checks)
            if success:
                pass
            else:
                print(f"  FAIL")
                print(f"  {msg[:cfg.max_error_message_length]}")
                total_errors += 1
        else:
            print("\n[4/5] Pipeline verification... SKIP (no config, use --config to specify)")
    else:
        print("\n[4/5] Pipeline verification... SKIP (use --pipeline to enable)")

    return total_errors


def _check_data(args, config_for_checks, cfg, total_errors):
    if args.data:
        if config_for_checks:
            print(f"\n[5/5] Data-loading check ({config_for_checks.name})...")
            success, msg = check_data_loading(args.path, config_for_checks, args.num_samples)
            if success:
                print(f"  {msg}")
            else:
                print(f"  FAIL")
                print(f"  {msg[:cfg.max_error_message_length]}")
                total_errors += 1
        else:
            print("\n[5/5] Data-loading check... SKIP (no config, use --config to specify)")
    else:
        print("\n[5/5] Data-loading check... SKIP (use --data to enable)")

    return total_errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify post-patch VLA compilation')
    parser.add_argument('path', type=Path, help='model codebase root path')
    parser.add_argument('--config', type=Path, help='config file for the model-build check')
    parser.add_argument('--runtime', action='store_true', help='run NPU runtime verification')
    parser.add_argument('--pipeline', action='store_true', help='run pipeline verification')
    parser.add_argument('--data', action='store_true', help='run data-loading verification')
    parser.add_argument('--num-samples', type=int, default=None, help='number of samples for the data-loading test')
    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: {args.path} does not exist")
        return 1

    cfg = get_config()
    if args.num_samples is None:
        args.num_samples = cfg.data_load_sample_count
    py_files = collect_py_files(args.path)

    total_errors = 0

    total_errors = _check_code_integrity(py_files, args.path, total_errors)

    found_config = _find_config(args, cfg)
    config_for_checks = args.config or found_config

    total_errors = _check_model_build(args, found_config, total_errors)
    total_errors = _check_runtime(args, total_errors)
    total_errors = _check_pipeline(args, config_for_checks, cfg, total_errors)
    total_errors = _check_data(args, config_for_checks, cfg, total_errors)

    if total_errors == 0:
        print("\n  All checks passed")
        return 0
    else:
        print(f"\n  {total_errors} error(s) found")
        return 1


_NOISY_SOURCES = [
    'transfer_to_npu.py',
    'transformers/modeling_utils.py',
    'transformers/configuration_utils.py',
    'datasets/',
    'scipy/sparse/coo',
]

_NOISY_STANDALONE = [
    'warnings.warn(',
    'INFO:datasets:',
    'WARNING:transformers:',
]


def _filter_stderr(raw: str) -> str:
    """Filter known noisy stderr sources from the verification output."""
    import re
    source_re = re.compile('|'.join(re.escape(s) for s in _NOISY_SOURCES))
    standalone_re = re.compile('|'.join(re.escape(s) for s in _NOISY_STANDALONE))
    filtered_lines = []
    skip_block = False
    for line in raw.split('\n'):
        if source_re.search(line):
            skip_block = True
        if skip_block:
            if 'warnings.warn(' in line or not line.strip():
                skip_block = False
            continue
        if standalone_re.search(line):
            continue
        if line.strip():
            filtered_lines.append(line)
    return '\n'.join(filtered_lines)


if __name__ == '__main__':
    stderr_capture = io.StringIO()
    exit_code = -1
    with redirect_stderr(stderr_capture):
        exit_code = main()
    stderr_content = stderr_capture.getvalue()
    filtered = _filter_stderr(stderr_content)
    if filtered:
        sys.stderr.write(filtered + '\n')
    exit(exit_code)
