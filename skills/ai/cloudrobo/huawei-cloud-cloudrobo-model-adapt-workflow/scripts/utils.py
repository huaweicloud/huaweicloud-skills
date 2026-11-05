from __future__ import annotations
"""VLA NPU Patcher utility functions.

Common operations shared by scan.py and verify.py.
Generic utilities — no model-specific dependencies.
"""

import re
from pathlib import Path
from config import get_config
from patterns import Issue


# --- Context extraction ---

def get_context(
    lines: list[str],
    lineno: int,
    before: int | None = None,
    after: int | None = None
) -> str:
    """Get the context around a line."""
    if before is None or after is None:
        cfg = get_config()
        default_ctx = cfg.context_windows.get('default', {'before': 3, 'after': 3})
        before = before if before is not None else default_ctx['before']
        after = after if after is not None else default_ctx['after']

    start = max(0, lineno - before - 1)
    end = min(len(lines), lineno + after)

    return '\n'.join(f"{i+1}: {lines[i]}" for i in range(start, end))


# --- Issue handling ---

def deduplicate_issues(issues: list[Issue]) -> list[Issue]:
    """Remove duplicate issues at the same location, keeping the first
    encountered."""
    by_location: dict[tuple[str, int, str], Issue] = {}

    for issue in issues:
        key = (issue.file, issue.line, issue.pattern_id)
        if key not in by_location:
            by_location[key] = issue

    return list(by_location.values())


# --- File filtering ---

def should_exclude(path: Path, exclude_dirs: set | None = None) -> bool:
    """Check whether a path should be excluded from scanning."""
    if exclude_dirs is None:
        exclude_dirs = get_config().exclude_dirs
    return any(part in exclude_dirs for part in path.parts)


def collect_py_files(root: Path) -> list[Path]:
    """Collect all Python files, excluding configured directories."""
    return [f for f in root.rglob('*.py') if not should_exclude(f)]


def read_py_file_content(f: Path) -> tuple[str, list[str]] | None:
    """Read a Python file's content and line list (with error handling)."""
    if f.suffix != '.py':
        return None
    try:
        content = f.read_text(encoding='utf-8', errors='ignore')
        return (content, content.split('\n'))
    except (OSError, UnicodeDecodeError):
        return None


def is_test_file(f: Path) -> bool:
    """Check whether a file is a test file (should be skipped by
    scanners)."""
    return any(pattern in str(f).lower() for pattern in get_config().test_file_patterns)


def is_config_file(f: Path) -> bool:
    """Check whether a file is a config file (should be skipped by some
    scanners)."""
    return 'configs' in str(f) or str(f).endswith('config.py')


def collect_sh_files(root: Path) -> list[Path]:
    """Collect all shell files, excluding configured directories."""
    return [f for f in root.rglob('*.sh') if not should_exclude(f)]
