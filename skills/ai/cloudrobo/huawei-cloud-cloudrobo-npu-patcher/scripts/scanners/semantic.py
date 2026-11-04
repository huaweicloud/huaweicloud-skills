"""SEMANTIC category scanner — semantic patterns requiring deep
analysis.

Pattern:
- P_TGT: target computation optimization opportunities
"""

from __future__ import annotations

import re
from pathlib import Path

from patterns import Issue
from .helpers import file_scanner
from config import get_config, get_context_config
from utils import get_context


def _tgt_has_optimizable_loop_patterns(context_text: str) -> bool:
    """Check whether context_text contains optimizable loop patterns."""
    has_loop = bool(re.search(r'for\s+\w+\s+in\s+range\s*\(', context_text))
    if not has_loop:
        return False

    has_weight_creation_in_loop = bool(
        re.search(r'for\s+\w+\s+in\s+range.*\n.*new_tensor\s*\(\s*self\.\w+_weights',
                  context_text, re.DOTALL)
    ) or bool(
        re.search(r'for\s+\w+\s+in\s+range.*\n.*\n.*new_tensor\s*\(\s*self\.\w+',
                  context_text, re.DOTALL)
    )

    has_neg_pos_in_loop = bool(
        re.search(r'for\s+\w+\s+in\s+range.*\n.*neg_cost\s*=',
                  context_text, re.DOTALL)
    )

    has_append_tensor = bool(
        re.search(r'outputs\.append\s*\(\s*output\s*\)', context_text)
    ) and bool(
        re.search(r'torch\.cat\s*\(', context_text)
    )

    has_indexed_assign = bool(
        re.search(r'\w+\[\s*\w+\s*,', context_text)
    ) and bool(
        re.search(r'=\s*gt_\w+\[', context_text)
    )

    return has_weight_creation_in_loop or has_neg_pos_in_loop or has_append_tensor or has_indexed_assign


@file_scanner()
def scan_p_tgt(f: Path, content: str, lines: list[str]) -> list[Issue]:
    """Scan P_TGT — target computation optimization opportunities.

    Detected patterns (function-independent):
    1. new_tensor(self.xxx_weights) inside a loop — should be pre-generated
    2. neg_cost/pos_cost computation inside a loop — should be extracted
       outside the loop
    3. outputs.append(tensor_op) inside a loop where tensor_op uses the
       loop variable — should be batched
    4. result[i] = tensor_assignment patterns inside a loop — should use
       gather

    Fix: batch operations, pre-generate tensors, use torch.gather.

    Semantics: requires understanding the function's purpose.
    """
    issues = []

    filename_has_signal = 'target' in str(f).lower() or 'cost' in str(f).lower()
    content_has_loss_class = bool(re.search(r'class\s+\w*[Ll]oss\w*\s*\(', content))
    content_has_target_cost_method = bool(re.search(r'def\s+\w*(?:target|cost|assign)\w*\s*\(', content))

    if not (filename_has_signal or content_has_loss_class or content_has_target_cost_method):
        return issues

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        if re.match(r'\s*def\s+\w+\s*\([^)]*self[^)]*\)', line):
            context_end = min(i + get_config().tgt_func_scan_lines, len(lines))
            context_text = '\n'.join(lines[i-1:context_end])

            if _tgt_has_optimizable_loop_patterns(context_text):
                ctx = get_context_config('P_TGT')
                issues.append(Issue(pattern_id='P_TGT', file=str(f), line=i,
                code=stripped[:get_config().code_snippet_length],
                context=get_context(lines, i, before=ctx['before'], after=ctx['after'])))

    return issues


__all__ = [
    'scan_p_tgt',
]
