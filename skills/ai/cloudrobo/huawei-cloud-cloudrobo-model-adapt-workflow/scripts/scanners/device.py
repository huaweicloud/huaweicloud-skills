"""DEVICE category scanner — NPU tensor device mismatch.

Pattern:
- P_RND: torch.rand/randn followed by .to(device)
"""

import ast
import re
from pathlib import Path

from patterns import Issue
from .helpers import file_scanner
from config import get_config, get_context_config
from utils import get_context


# ----------------------------------------------------------------
# P_RND helper functions
# ----------------------------------------------------------------

def _rnd_has_multiline_to_device(line: str, lines: list[str], i: int, cfg) -> bool:
    for j in range(i, min(i + cfg.lookahead_lines, len(lines) + 1)):
        next_line = lines[j - 1] if j <= len(lines) else ''
        if '.to(' in next_line and 'device' in next_line:
            var_match = re.match(r'\s*(\w+)\s*=', line)
            if var_match:
                var_name = var_match.group(1)
                if f'{var_name}.to(' in next_line or f'{var_name} = {var_name}.to(' in next_line:
                    return True
    return False


@file_scanner(skip_tests=True)
def scan_p_rnd(f: Path, _content: str, lines: list[str]) -> list[Issue]:
    """Scan P_RND — torch.rand/randn followed by .to(device).

    Problem: torch.rand(shape).to(device) creates on CPU then transfers.
    Fix: torch.rand(shape, device=device) creates directly on the target
    device.

    Detects:
    - torch.rand(...).to(device)
    - torch.randn(...).to(device)
    - torch.randint(...).to(device)
    - multiline: a rand call with .to() on the next line

    False positives to skip:
    - already has a device= argument
    - .to('cpu') — no transfer needed
    - torch.rand_like() — uses the input's device
    """
    issues = []
    cfg = get_config()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        has_rand_call = any(func in line for func in cfg.random_functions)
        if not has_rand_call:
            continue

        if 'rand_like' in line or 'randn_like' in line:
            continue

        if 'device=' in line:
            continue

        if '_like(' in line:
            continue

        has_to_device = False
        to_device_match = re.search(r'\.to\s*\(\s*(device\s*=|[^)]*(?:npu|cuda|device))', line)
        if to_device_match:
            has_to_device = True

        if not has_to_device:
            has_to_device = _rnd_has_multiline_to_device(line, lines, i, cfg)

        if has_to_device:
            if re.search(r'\.to\s*\(\s*(device\s*=\s*)?["\']cpu["\']', line):
                continue
            ctx = get_context_config('P_RND')
            issues.append(Issue(
                pattern_id='P_RND', file=str(f), line=i,
                code=stripped[:cfg.code_snippet_length],
                context=get_context(lines, i, before=ctx['before'], after=ctx['after'])))

    return issues


__all__ = [
    'scan_p_rnd',
]
