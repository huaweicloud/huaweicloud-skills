"""VLA NPU Patcher scanners.

Package-level API: IssueGroup, group_issues_for_agent, PY_SCANNERS.

Scanners are auto-discovered by naming convention:
- scan_p_* functions are pattern scanners (collected from all scanner
  modules)

VLA scanners (no autonomous-driving-specific scanners):
- device.py:     P_RND (torch.rand + .to(device))
- operator.py:   P_FLA (VLA's flash_attn imports)
- structure.py:  P_ENT (entry points), P_VEC (loop vectorization)
- framework.py:  P_LTM (pytorch_lightning.metrics)
- semantic.py:   P_TGT (target computation optimization)

Removed from ascend-driving-patcher:
- dtype.py:      P_FLT (now the PowFloatSafe runtime patch)
- operator.py:   P_DAG, P_M6F, P_MUL (autonomous-driving-specific)
- framework.py:  P_ADW (now the AdamWFused runtime patch)
"""

from dataclasses import dataclass

from patterns import Issue

from . import device, operator, structure, framework, semantic


@dataclass
class IssueGroup:
    pattern_id: str
    count: int
    occurrences: list[dict]


def group_issues_for_agent(issues: list[Issue]) -> list[IssueGroup]:
    """Group issues by Pattern ID so the Agent can review them
    efficiently."""
    by_pattern: dict[str, list[Issue]] = {}
    for issue in issues:
        by_pattern.setdefault(issue.pattern_id, []).append(issue)

    groups = []
    for pattern_id, pattern_issues in by_pattern.items():
        minimal_occurrences = []
        for i in pattern_issues:
            occ = {'file': i.file, 'line': i.line}
            if i.issue_id is not None:
                occ['issue_id'] = i.issue_id
            minimal_occurrences.append(occ)
        groups.append(IssueGroup(
            pattern_id=pattern_id,
            count=len(pattern_issues),
            occurrences=minimal_occurrences,
        ))

    groups.sort(key=lambda g: g.count, reverse=True)
    return groups


def _collect_scanners(module) -> list:
    return [
        getattr(module, name)
        for name in dir(module)
        if name.startswith('scan_p_')
    ]


PY_SCANNERS = (
    _collect_scanners(device)
    + _collect_scanners(operator)
    + _collect_scanners(structure)
    + _collect_scanners(framework)
    + _collect_scanners(semantic)
)

__all__ = [
    'IssueGroup',
    'group_issues_for_agent',
    'PY_SCANNERS',
]
