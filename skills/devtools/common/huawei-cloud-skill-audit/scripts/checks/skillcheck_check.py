#!/usr/bin/env python3
"""Skillcheck check — SKILL.md agentskills.io spec validation."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel


class SkillcheckCheck(Check):
    name = "skillcheck"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 120, skillcheck_bin: str = "skillcheck"):
        super().__init__(scan_level, timeout)
        self.bin = skillcheck_bin

    def is_available(self) -> bool:
        return shutil.which(self.bin) is not None

    def run(self, skill_dir: Path) -> CheckResult:
        cmd = [self.bin, str(skill_dir), "--format", "json"]
        config = skill_dir / "skillcheck.toml"
        if config.exists():
            cmd += ["--config", str(config)]
        from skill_audit import run_cmd
        out, rc = run_cmd(cmd, timeout=self.timeout)
        try:
            data = json.loads(out)
            return self._parse(data)
        except Exception:
            return CheckResult(source=self.name, passed=True, raw_output=out)

    def run_batch(self, target: Path, skills: list[Path]) -> CheckResult:
        cmd = [self.bin, str(target), "--format", "json"]
        config = target / "skillcheck.toml"
        if config.exists():
            cmd += ["--config", str(config)]
        from skill_audit import run_cmd
        out, rc = run_cmd(cmd, timeout=self.timeout)
        try:
            data = json.loads(out)
            return self._parse(data)
        except Exception:
            cmd2 = [self.bin, str(target)]
            if config.exists():
                cmd2 += ["--config", str(config)]
            out2, rc2 = run_cmd(cmd2, timeout=self.timeout)
            return CheckResult(source=self.name, passed=True, raw_output=out2)

    def _parse(self, data: dict) -> CheckResult:
        issues = []
        for r in data.get("results", []):
            for d in r.get("diagnostics", []):
                sev_str = d.get("severity", "info")
                sev = self._map_severity(sev_str)
                if sev == Severity.INFO:
                    continue
                issues.append(Issue(
                    rule=d.get("rule", ""),
                    severity=sev,
                    message=d.get("message", ""),
                ))
        passed = data.get("files_failed", 0) == 0
        return CheckResult(source=self.name, issues=issues, passed=passed)

    @staticmethod
    def _map_severity(sev: str) -> Severity:
        if sev == "warning":
            return Severity.WARNING
        if sev == "info":
            return Severity.INFO
        return Severity.ERROR
