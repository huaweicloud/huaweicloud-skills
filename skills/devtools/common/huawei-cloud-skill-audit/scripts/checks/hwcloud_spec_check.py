#!/usr/bin/env python3
"""Huawei Cloud spec check — SKILL.md frontmatter/section/size compliance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel


class HwcloudSpecCheck(Check):
    name = "hwcloud-spec"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD, timeout: int = 0):
        super().__init__(scan_level, timeout)

    def is_available(self) -> bool:
        return True

    def run(self, skill_dir: Path) -> CheckResult:
        from hwcloud_spec_check import run_hwcloud_spec_check
        result = run_hwcloud_spec_check(skill_dir)
        issues = []
        for iss in result.get("issues", []):
            sev_str = iss.get("severity", "warning")
            sev = Severity.ERROR if sev_str == "error" else (
                Severity.WARNING if sev_str == "warning" else Severity.INFO
            )
            if sev == Severity.INFO:
                continue
            issues.append(Issue(
                rule=iss.get("rule", ""),
                severity=sev,
                message=iss.get("message", ""),
                category=iss.get("category", iss.get("rule", "").split(".")[0]),
            ))
        return CheckResult(
            source=self.name,
            issues=issues,
            passed=len(issues) == 0,
        )
