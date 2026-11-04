"""OPERATOR category scanner — NPU operator compatibility for VLA.

Pattern:
- P_FLA: Flash Attention imports (VLA: flash_attn package / transformers)
"""

from __future__ import annotations

import re
from pathlib import Path

from patterns import Issue
from .helpers import file_scanner
from config import get_context_config
from utils import get_context


def _make_p_fla_issue(f: Path, lines: list[str], i: int, code: str) -> Issue:
    ctx = get_context_config('P_FLA')
    return Issue(pattern_id='P_FLA', file=str(f), line=i,
    code=code,
    context=get_context(lines, i, before=ctx['before'], after=ctx['after']))


# Matches attn_implementation = "value" (assignment, not comparison ==)
# Covers: variable assignment, dict assignment, function keyword arguments
# Match examples:
#   attn_implementation = "sdpa"
#   extra_kwargs["attn_implementation"] = "sdpa"
#   attn_implementation="sdpa"
# Non-match examples:
#   if attn_implementation == "sdpa":  (comparison, == instead of =)
_ATTN_IMPL_RE = re.compile(
    r'''attn_implementation\s*['"]?\]?\s*=(?!=)\s*['"]([^'"]+)['"]'''
)

# Attention implementations other than flash_attention_2.
# If flash_attention_2 appears elsewhere in the file, these values indicate
# a fallback that should keep flash_attention_2 on NPU (P_FLA fix template
# scenario 2).
_NON_FLASH_IMPLS = {'sdpa', 'eager'}


@file_scanner(skip_tests=True)
def scan_p_fla(f: Path, content: str, lines: list[str]) -> list[Issue]:
    """Scan P_FLA — Flash Attention requiring an NPU implementation (VLA).

    Detects two classes of issues:

    1. flash_attn imports (will crash on NPU):
       - direct import flash_attn, not inside a try block, no
         FLASH_ATTN_AVAILABLE guard

    2. flash_attention_2 fallback logic (P_FLA fix template scenario 2):
       - the file uses "flash_attention_2", but an except/else branch falls
         back to "sdpa"/"eager"
       - on NPU (transformers >= 4.57) "flash_attention_2" should be kept
       - only report attn_implementation assignment lines with a value other
         than "flash_attention_2" when "flash_attention_2" exists in the
         file
       - do not report when the source only uses sdpa/eager (no
         flash_attention_2)
    """
    issues = []

    # --- Scenario 1: direct flash_attn imports (crash on NPU) ---
    has_flash_attn_available = 'FLASH_ATTN_AVAILABLE' in content
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if 'flash_attn' in line and 'import' in line:
            if has_flash_attn_available:
                continue
            if 'try:' in (lines[i-2] if i > 1 else ''):
                continue
            issues.append(_make_p_fla_issue(f, lines, i, stripped))

    # --- Scenario 2: flash_attention_2 falls back to non-flash_attention_2 ---
    # Only detect when "flash_attention_2" exists in the file (non-comment
    # lines)
    has_flash_attention_2 = any(
        'flash_attention_2' in line and not line.strip().startswith('#')
        for line in lines
    )
    if has_flash_attention_2:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            m = _ATTN_IMPL_RE.search(stripped)
            if m and m.group(1) in _NON_FLASH_IMPLS:
                issues.append(_make_p_fla_issue(f, lines, i, stripped))

    return issues


__all__ = [
    'scan_p_fla',
]
