#!/usr/bin/env python3
"""Check registry — AuditConfig, check catalog, and factory."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from check_protocol import Check, ScanLevel


@dataclass
class AuditConfig:
    scan_level: str = "high"
    enabled_checks: set[str] = field(default_factory=lambda: set(DEFAULT_ENABLED_CHECKS))
    check_timeouts: dict[str, int] = field(default_factory=lambda: {
        "skillspector": 30, "gitleaks": 30, "runtime_security": 30,
    })
    check_bins: dict[str, str] = field(default_factory=dict)
    no_install: bool = False
    node_bin: str = ""


# 全部可用检查集合(白名单, resolve_enabled_checks 校验用)
AVAILABLE_CHECKS = {
    "skillspector", "gitleaks", "runtime_security",
}

# 默认启用集合(与 AVAILABLE_CHECKS 一致; 变更时需同步 AuditConfig.enabled_checks 默认值)
DEFAULT_ENABLED_CHECKS = set(AVAILABLE_CHECKS)


def resolve_enabled_checks(checks_arg: str | None, skip_arg: str | None) -> set[str]:
    """Resolve --checks and --skip-checks into final enabled set."""
    if checks_arg and skip_arg:
        raise ValueError("Cannot use --checks and --skip-checks together")
    if checks_arg:
        selected = {c.strip() for c in checks_arg.split(",")}
        invalid = selected - AVAILABLE_CHECKS
        if invalid:
            raise ValueError(f"Unknown checks: {invalid}. Available: {sorted(AVAILABLE_CHECKS)}")
        return selected
    enabled = set(DEFAULT_ENABLED_CHECKS)
    if skip_arg:
        skipped = {c.strip() for c in skip_arg.split(",")}
        invalid = skipped - AVAILABLE_CHECKS
        if invalid:
            raise ValueError(f"Unknown checks in --skip-checks: {invalid}")
        enabled -= skipped
    return enabled


def _resolve_gitleaks_check(scan_level, timeout, bin_path):
    """Return gitleaks check instance (fail-closed).

    Priority:
    1. External gitleaks binary — ONLY when explicitly provided via ``--gitleaks``
    2. Built-in pure Python implementation (always available if rules JSON exists)

    PATH 自动发现已禁用(2026-09-23, 审查意见): 不再 ``shutil.which`` 探测 PATH,
    避免 PATH 被注入同名恶意二进制静默接管审计。外部二进制必须显式指定。
    """
    from checks.gitleaks_builtin_check import GitleaksBuiltinCheck

    if bin_path:
        from checks.gitleaks_check import GitleaksCheck
        return GitleaksCheck(scan_level=scan_level, timeout=timeout, gitleaks_bin=bin_path)

    return GitleaksBuiltinCheck(scan_level=scan_level, timeout=timeout)


def _resolve_skillspector_check(scan_level, timeout, bin_path):
    """Return skillspector check instance (fail-closed).

    Priority:
    1. External skillspector binary — ONLY when explicitly provided via ``--skillspector``
    2. Built-in pure Python implementation (always available if rules JSON exists)

    PATH 自动发现已禁用(2026-09-23, 审查意见): 不再 ``shutil.which`` 探测 PATH,
    避免 PATH 被注入同名恶意二进制静默接管审计。外部二进制必须显式指定;
    critical/high 档若未显式指定外部二进制则恒 builtin(外部二进制不支持该档位)。
    """
    from checks.skillspector_builtin_check import SkillspectorBuiltinCheck

    # 显式提供的外部二进制优先于档位判断(与 Priority 1 一致), 避免用户在
    # critical/high 档显式传 --skillspector 被静默忽略。
    if bin_path:
        from checks.skillspector_check import SkillspectorCheck
        return SkillspectorCheck(scan_level=scan_level, timeout=timeout, skillspector_bin=bin_path)

    if scan_level.value in ("critical", "high"):
        return SkillspectorBuiltinCheck(scan_level=scan_level, timeout=timeout)

    return SkillspectorBuiltinCheck(scan_level=scan_level, timeout=timeout)


def _resolve_runtime_security_check(scan_level, timeout):
    """RuntimeSecurityCheck — CWE 高危模式检查器(纯 Python, 级别无关)。"""
    from checks.runtime_security_check import RuntimeSecurityCheck
    return RuntimeSecurityCheck(scan_level=scan_level, timeout=timeout)


def create_checks(config: AuditConfig) -> list:
    """Instantiate enabled checks based on config. Returns list of Check instances."""
    from check_protocol import ScanLevel

    scan_level = ScanLevel(config.scan_level)
    checks = []
    for name in sorted(config.enabled_checks):
        timeout = config.check_timeouts.get(name, 30)
        bin_path = config.check_bins.get(name, "")

        if name == "skillspector":
            checks.append(_resolve_skillspector_check(scan_level, timeout, bin_path))
        elif name == "gitleaks":
            checks.append(_resolve_gitleaks_check(scan_level, timeout, bin_path))
        elif name == "runtime_security":
            checks.append(_resolve_runtime_security_check(scan_level, timeout))
        # TODO: skillcheck / markdownlint / hwcloud-spec checker 文件存在但暂未接入
        # (AVAILABLE_CHECKS 只启用上三检); 需要时在 resolve_enabled_checks 白名单
        # 与下方分支中启用。

    return checks
