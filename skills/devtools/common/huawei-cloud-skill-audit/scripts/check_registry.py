#!/usr/bin/env python3
"""Check registry — AuditConfig, check catalog, and factory."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from check_protocol import Check, ScanLevel


@dataclass
class AuditConfig:
    scan_level: str = "critical"
    enabled_checks: set[str] = field(default_factory=lambda: {
        "skillspector", "gitleaks",
    })
    check_timeouts: dict[str, int] = field(default_factory=lambda: {
        "skillspector": 30, "gitleaks": 30,
    })
    check_bins: dict[str, str] = field(default_factory=dict)
    no_install: bool = False
    node_bin: str = ""


DEFAULT_CHECKS = {
    "skillspector", "gitleaks",
}


def resolve_enabled_checks(checks_arg: str | None, skip_arg: str | None) -> set[str]:
    """Resolve --checks and --skip-checks into final enabled set."""
    if checks_arg and skip_arg:
        raise ValueError("Cannot use --checks and --skip-checks together")
    if checks_arg:
        selected = {c.strip() for c in checks_arg.split(",")}
        invalid = selected - DEFAULT_CHECKS
        if invalid:
            raise ValueError(f"Unknown checks: {invalid}. Available: {sorted(DEFAULT_CHECKS)}")
        return selected
    enabled = set(DEFAULT_CHECKS)
    if skip_arg:
        skipped = {c.strip() for c in skip_arg.split(",")}
        invalid = skipped - DEFAULT_CHECKS
        if invalid:
            raise ValueError(f"Unknown checks in --skip-checks: {invalid}")
        enabled -= skipped
    return enabled


def _resolve_gitleaks_check(scan_level, timeout, bin_path):
    """Return the best available gitleaks check instance.

    Priority:
    1. External gitleaks binary (if found on PATH or explicitly provided)
    2. Built-in pure Python implementation (always available if rules JSON exists)
    """
    import shutil
    from checks.gitleaks_builtin_check import GitleaksBuiltinCheck

    resolved_bin = bin_path or "gitleaks"
    if shutil.which(resolved_bin):
        from checks.gitleaks_check import GitleaksCheck
        return GitleaksCheck(scan_level=scan_level, timeout=timeout, gitleaks_bin=resolved_bin)

    return GitleaksBuiltinCheck(scan_level=scan_level, timeout=timeout)


def _resolve_skillspector_check(scan_level, timeout, bin_path):
    """Return the best available skillspector check instance.

    Priority:
    1. Built-in pure Python for critical/high levels (external binary doesn't support these)
    2. External skillspector binary (if found on PATH or explicitly provided)
    3. Built-in pure Python implementation (fallback)
    """
    import shutil
    from checks.skillspector_builtin_check import SkillspectorBuiltinCheck

    if scan_level.value in ("critical", "high"):
        return SkillspectorBuiltinCheck(scan_level=scan_level, timeout=timeout)

    resolved_bin = bin_path or "skillspector"
    if shutil.which(resolved_bin):
        from checks.skillspector_check import SkillspectorCheck
        return SkillspectorCheck(scan_level=scan_level, timeout=timeout, skillspector_bin=resolved_bin)

    return SkillspectorBuiltinCheck(scan_level=scan_level, timeout=timeout)


def create_checks(config: AuditConfig) -> list:
    """Instantiate enabled checks based on config. Returns list of Check instances."""
    from check_protocol import ScanLevel
    from checks.skillcheck_check import SkillcheckCheck
    from checks.markdownlint_check import MarkdownlintCheck
    from checks.skillspector_check import SkillspectorCheck
    from checks.hwcloud_spec_check import HwcloudSpecCheck

    scan_level = ScanLevel(config.scan_level)
    checks = []
    for name in sorted(config.enabled_checks):
        if name not in config.enabled_checks:
            continue
        timeout = config.check_timeouts.get(name, 30)
        bin_path = config.check_bins.get(name, "")

        if name == "skillspector":
            checks.append(_resolve_skillspector_check(scan_level, timeout, bin_path))
        elif name == "gitleaks":
            checks.append(_resolve_gitleaks_check(scan_level, timeout, bin_path))

    return checks
