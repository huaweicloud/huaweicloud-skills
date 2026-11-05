from __future__ import annotations
"""VLA NPU Patcher Pattern registry — the single source of truth for all
Patterns.

This module centrally manages all Pattern definitions to keep consistency
across:
- scanner registration (registry.py)
- category mapping (config.py)
- documentation (SKILL.md)

Patterns now handled by runtime patches (removed from scanners):
- P_FLT: torch.pow fractional exponent → PowFloatSafe runtime patch
- P_ADW: AdamW → NpuFusedAdamW → AdamWFused runtime patch

Retained Patterns (require source-level fixes):
- P_RND: torch.rand + .to(device) (requires static analysis)
- P_ENT: entry point NPU wrapping (the activator of the runtime patches)
- P_VEC: loop vectorization (requires code refactoring)
- P_LTM: pytorch_lightning.metrics import (requires import path change)
- P_TGT: target computation optimization (requires algorithmic
  understanding)
- P_FLA: flash_attn import (handled case by case)
"""
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Issue:
    pattern_id: str
    file: str
    line: int
    code: str = ""
    context: str | None = None
    issue_id: str | None = None


class Category(Enum):
    """Pattern categories."""
    DEVICE = 'DEVICE'           # NPU tensor device mismatch
    OPERATOR = 'OPERATOR'       # CUDA extensions → NPU API
    STRUCTURE = 'STRUCTURE'     # loops, initialization, entry points
    FRAMEWORK = 'FRAMEWORK'     # pytorch_lightning, transformers
    SEMANTIC = 'SEMANTIC'       # optimization


_DEFAULT_CONTEXT_WINDOW = {'before': 3, 'after': 3}


@dataclass
class PatternInfo:
    id: str
    category: Category
    description: str
    problem: str = ""
    fix_hint: str = ""
    context_window: dict[str, int] = field(default_factory=lambda: dict(_DEFAULT_CONTEXT_WINDOW))
    notes: str = ""


# =============================================================================
# PATTERN DEFINITIONS — single source of truth
# =============================================================================

PATTERNS: dict[str, PatternInfo] = {
    # =========================================================================
    # DEVICE category — NPU tensor device mismatch
    # =========================================================================
    'P_RND': PatternInfo(
        id='P_RND',
        category=Category.DEVICE,
        description='torch.rand followed by .to(device)',
        problem='Random tensors are created on CPU then moved to the device, which is inefficient.',
        fix_hint='Create directly on the target device: torch.rand(..., device=device)',
        context_window={'before': 5, 'after': 5},
    ),

    # =========================================================================
    # OPERATOR category — CUDA extensions → NPU API
    # =========================================================================
    'P_FLA': PatternInfo(
        id='P_FLA',
        category=Category.OPERATOR,
        description='Flash Attention NPU implementation (flash_attn import + flash_attention_2 fallback logic)',
        problem='The flash_attn package is a CUDA-only library and cannot be imported on NPU. '
                'VLA models may depend on flash_attn directly or indirectly. '
                'When the source uses flash_attention_2 but falls back to sdpa/eager in the '
                'except branch, flash_attention_2 should be kept on NPU '
                '(transformers >= 4.57).',
        fix_hint='Choose per scenario, using an NPU-compatible attention implementation. '
                 'See the P_FLA fix template for details.',
        context_window={'before': 5, 'after': 10},
    ),

    # =========================================================================
    # STRUCTURE category — loops, initialization, entry points
    # =========================================================================
    'P_ENT': PatternInfo(
        id='P_ENT',
        category=Category.STRUCTURE,
        description='Entry point needs NPU wrapping',
        problem='The VLA training/inference entry point lacks NPU initialization.',
        fix_hint='Add NPU device setup and a build_vla_patcher() wrapper.',
        context_window={'before': 0, 'after': 5},
    ),
    'P_VEC': PatternInfo(
        id='P_VEC',
        category=Category.STRUCTURE,
        description='Vectorizable tensor loops or list-append-then-cat patterns',
        problem='Loops or append-then-cat patterns can be vectorized to improve NPU efficiency. '
                'Loops with small iteration counts and list-append-then-torch.cat patterns '
                'cause unnecessary kernel launches and memory copies on NPU.',
        fix_hint='Replace loops with torch operations. Replace list.append() + torch.cat() '
                 'with preallocated tensors or torch.stack().',
        context_window={'before': 2, 'after': 10},
        notes='Python loops over tensor indexing cause 100x+ slowdowns on NPU '
              'because every iteration requires a CPU/NPU sync.',
    ),

    # =========================================================================
    # FRAMEWORK category — pytorch_lightning, transformers
    # =========================================================================

    'P_LTM': PatternInfo(
        id='P_LTM',
        category=Category.FRAMEWORK,
        description='pytorch_lightning.metrics import (deprecated)',
        problem='The pytorch_lightning.metrics module structure has changed. '
                'Metrics have moved to the torchmetrics package.',
        fix_hint='Update the import: from pytorch_lightning.metrics → from torchmetrics',
        context_window={'before': 3, 'after': 3},
    ),

    # =========================================================================
    # SEMANTIC category — gradients, optimization
    # =========================================================================

    'P_TGT': PatternInfo(
        id='P_TGT',
        category=Category.SEMANTIC,
        description='Target computation optimization',
        problem='Target computation can be optimized (batch operations).',
        fix_hint='Batch operations, pre-generate tensors, use torch.gather.',
        context_window={'before': 3, 'after': 3},
    ),
}


# =============================================================================
# Registry functions
# =============================================================================

def get_pattern(pattern_id: str) -> PatternInfo | None:
    return PATTERNS.get(pattern_id)


def get_patterns_by_category(category: Category) -> list[PatternInfo]:
    return [p for p in PATTERNS.values() if p.category == category]


def get_pattern_ids() -> set[str]:
    return set(PATTERNS.keys())


def get_context_windows() -> dict[str, dict[str, int]]:
    windows = {'default': dict(_DEFAULT_CONTEXT_WINDOW)}
    for pid, info in PATTERNS.items():
        if info.context_window != _DEFAULT_CONTEXT_WINDOW:
            windows[pid] = dict(info.context_window)
    return windows


# =============================================================================
# Integrity checks
# =============================================================================

def _check_duplicate_ids(issues, verbose):
    seen_ids = set()
    for pattern_id, info in PATTERNS.items():
        if info.id != pattern_id:
            issue = f"Pattern key '{pattern_id}' does not match info.id '{info.id}'"
            issues.append(issue)
            if verbose:
                print(f"ERROR: {issue}")
        if info.id in seen_ids:
            issue = f"Duplicate pattern ID: {info.id}"
            issues.append(issue)
            if verbose:
                print(f"ERROR: {issue}")
        seen_ids.add(info.id)
    return issues


def _check_field_validity(pattern_id, info, issues, verbose):
    if not isinstance(info.category, Category):
        issue = f"Pattern {pattern_id} has invalid category: {info.category}"
        issues.append(issue)
        if verbose:
            print(f"ERROR: {issue}")
    return issues


def _print_integrity_summary(issues):
    print(f"\nPattern Registry Summary:")
    print(f"   Total patterns: {len(PATTERNS)}")
    if issues:
        print(f"\n   {len(issues)} integrity issue(s) found")
    else:
        print(f"\n   All patterns pass integrity check")


def check_integrity(verbose: bool = False) -> list[str]:
    issues = []
    issues = _check_duplicate_ids(issues, verbose)
    for pattern_id, info in PATTERNS.items():
        issues = _check_field_validity(pattern_id, info, issues, verbose)
    if verbose:
        _print_integrity_summary(issues)
    return issues


def _validate_on_import():
    issues = check_integrity(verbose=False)
    if issues:
        import sys
        print(f"WARNING: Pattern registry loaded with {len(issues)} issue(s)", file=sys.stderr)


_validate_on_import()
