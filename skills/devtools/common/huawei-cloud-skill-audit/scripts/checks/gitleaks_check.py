#!/usr/bin/env python3
"""Gitleaks check — credential leak detection."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel


class GitleaksCheck(Check):
    name = "gitleaks"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 30, gitleaks_bin: str = "gitleaks"):
        super().__init__(scan_level, timeout)
        self.bin = gitleaks_bin

    def is_available(self) -> bool:
        return shutil.which(self.bin) is not None

    def run(self, skill_dir: Path) -> CheckResult:
        report_file = tempfile.mktemp(suffix=".json")
        cmd = [self.bin, "detect", "--source", str(skill_dir),
               "--no-banner", "--no-git",
               "--report-format", "json", "--report-path", report_file]
        from skill_audit import run_cmd
        out, rc = run_cmd(cmd, timeout=self.timeout)
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                findings = json.load(f)
            os.unlink(report_file)
            return self._parse(findings, skill_dir.name)
        except Exception:
            if os.path.exists(report_file):
                os.unlink(report_file)
            return CheckResult(source=self.name, passed=True, raw_output=out)

    @staticmethod
    def _parse(findings: list, skill_name: str) -> CheckResult:
        issues = []
        for f in findings:
            rule_id = f.get("RuleID", "unknown")
            match = f.get("Match", "")
            snippet = match[:80] + "..." if len(match) > 80 else match
            issues.append(Issue(
                rule=rule_id,
                severity=Severity.ERROR,
                message=f.get("Description", rule_id),
                line=f.get("StartLine", 0),
                snippet=snippet,
                category=rule_id,
            ))
        return CheckResult(
            source="gitleaks",
            issues=issues,
            passed=len(issues) == 0,
        )
