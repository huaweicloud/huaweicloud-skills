#!/usr/bin/env python3
"""Markdownlint check — Markdown style consistency."""

import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel


class MarkdownlintCheck(Check):
    name = "markdownlint"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 60, markdownlint_bin: str = "markdownlint-cli2",
                 node_bin: str = ""):
        super().__init__(scan_level, timeout)
        self.bin = markdownlint_bin
        self.node_bin = node_bin

    def is_available(self) -> bool:
        ml = os.path.join(self.node_bin, self.bin) if self.node_bin else self.bin
        return shutil.which(ml) is not None

    def run(self, skill_dir: Path) -> CheckResult:
        return self._run_on_path(skill_dir)

    def run_batch(self, target: Path, skills: list[Path]) -> CheckResult:
        return self._run_on_path(target)

    def _run_on_path(self, target: Path) -> CheckResult:
        ml = os.path.join(self.node_bin, self.bin) if self.node_bin else self.bin
        config = target / ".markdownlint.json"
        glob_pattern = str(target / "**" / "*.md")
        cmd = [ml, glob_pattern, "--config", str(config)] if config.exists() else [ml, glob_pattern]
        from skill_audit import run_cmd
        out, rc = run_cmd(cmd, timeout=self.timeout)
        issues = self._parse(out)
        return CheckResult(source=self.name, issues=issues, passed=rc == 0)

    @staticmethod
    def _parse(raw: str) -> list[Issue]:
        issues = []
        pat = re.compile(r'^(.+?):(\d+):?(\d+)?\s+(MD\d+/\S+)\s+(.*)$', re.MULTILINE)
        for m in pat.finditer(raw):
            issues.append(Issue(
                rule=m.group(4),
                severity=Severity.ERROR,
                message=m.group(5).strip(),
                line=int(m.group(2)),
                category=m.group(4).split("/")[0],
            ))
        return issues
