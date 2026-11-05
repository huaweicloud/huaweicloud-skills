"""FRAMEWORK category scanner — pytorch_lightning, transformers.

Pattern:
- P_LTM: pytorch_lightning.metrics import (deprecated)

Removed from ascend-driving-patcher:
- P_ADW: AdamW → NpuFusedAdamW (now handled by the AdamWFused runtime
  patch)
"""

import ast
from pathlib import Path

from patterns import Issue
from .helpers import file_scanner
from utils import get_context
from config import get_context_config


@file_scanner()
def scan_p_ltm(f: Path, content: str, lines: list[str]) -> list[Issue]:
    """P_LTM: pytorch_lightning.metrics import (deprecated)."""
    issues = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and 'pytorch_lightning.metrics' in node.module:
                issues.append(Issue(pattern_id='P_LTM', file=str(f), line=node.lineno,
                code=lines[node.lineno - 1].strip(),
                context=get_context(lines, node.lineno)))
    return issues


__all__ = [
    'scan_p_ltm',
]
