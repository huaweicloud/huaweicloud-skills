#!/usr/bin/env python
"""Mask sensitive values (AK, SK, passwords) in script output.

Provides a masking utility for Huawei Cloud SAC scripts.
Any output containing access_key, secret_key, or password values
must be masked to prevent credential leakage.
"""

from __future__ import annotations

import re
from typing import Any

# Keys whose values should always be masked in output.
SENSITIVE_KEY_PATTERNS = [
    re.compile(r"(?:access_key|secret_key|password|passwd|token|secret)", re.IGNORECASE),
]

# Minimum length before partial reveal (show last 4 chars).
REVEAL_THRESHOLD = 8


def mask_value(value: str, visible_tail: int = 4) -> str:
    """Mask a sensitive value, optionally revealing the last N characters.

    Args:
        value: The sensitive string to mask.
        visible_tail: Number of trailing characters to reveal (default 4).

    Returns:
        Masked string like "****abcd" or "***" for short values.
    """
    if not value:
        return "***"
    if len(value) >= REVEAL_THRESHOLD and visible_tail > 0:
        return f"****{value[-visible_tail:]}"
    return "***"


def is_sensitive_key(key: str) -> bool:
    """Check if a key name refers to a sensitive field."""
    return any(p.search(key) for p in SENSITIVE_KEY_PATTERNS)


def mask_dict(data: dict[str, Any], visible_tail: int = 4) -> dict[str, Any]:
    """Return a copy of the dict with sensitive values masked.

    Args:
        data: Dictionary that may contain sensitive key-value pairs.
        visible_tail: Number of trailing characters to reveal.

    Returns:
        New dict with sensitive values replaced by masked strings.
    """
    result = {}
    for key, value in data.items():
        if is_sensitive_key(key) and isinstance(value, str):
            result[key] = mask_value(value, visible_tail)
        else:
            result[key] = value
    return result


def mask_line(line: str, visible_tail: int = 4) -> str:
    """Mask sensitive key=value patterns in a single output line.

    Handles formats like:
        access_key=ABCDEF123456
        "access_key": "ABCDEF123456"
        access_key : ABCDEF123456

    Args:
        line: A single line of output text.
        visible_tail: Number of trailing characters to reveal.

    Returns:
        The line with sensitive values masked.
    """
    # Pattern: key = value  or  key: value  or  "key": "value"
    pattern = re.compile(
        r"""(
            (?:access_key|secret_key|password|passwd|token|secret)
            \s*(?:=|:)\s*
        )
        (?:
            "([^"]*)"
            |
            '([^']*)'
            |
            (\S+)
        )""",
        re.IGNORECASE | re.VERBOSE,
    )

    def _replace(m: re.Match) -> str:
        prefix = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or ""
        return f"{prefix}{mask_value(value, visible_tail)}"

    return pattern.sub(_replace, line)
