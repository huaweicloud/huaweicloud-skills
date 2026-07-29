#!/usr/bin/env python3
"""SkillSpector check — AI skill security scanner (replaces skill-scanner)."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel


class SkillspectorCheck(Check):
    name = "skillspector"

    ANALYZER_GROUPS = {
        ScanLevel.QUICK: [
            "static_patterns_prompt_injection",
            "static_patterns_data_exfiltration",
            "static_patterns_privilege_escalation",
            "static_patterns_harmful_content",
            "static_yara",
        ],
        ScanLevel.STANDARD: None,
        ScanLevel.DEEP: None,
    }

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 30, skillspector_bin: str = "skillspector"):
        super().__init__(scan_level, timeout)
        self.bin = skillspector_bin

    def is_available(self) -> bool:
        return shutil.which(self.bin) is not None

    def run(self, skill_dir: Path) -> CheckResult:
        cmd = [self.bin, "scan", str(skill_dir), "--no-llm", "-f", "json"]
        analyzers = self.ANALYZER_GROUPS.get(self.scan_level)
        if analyzers:
            cmd += ["--analyzers", ",".join(analyzers)]
        from skill_audit import run_cmd
        out, rc = run_cmd(cmd, timeout=self.timeout)
        if rc == 137 or "Killed" in out:
            return CheckResult(source=self.name, passed=True, raw_output="TIMEOUT (killed)")
        try:
            data = json.loads(out)
            return self._parse(data)
        except json.JSONDecodeError:
            return CheckResult(source=self.name, passed=True, raw_output=out)

    def _parse(self, data: dict) -> CheckResult:
        issues = []
        for finding in data.get("issues", []):
            sev = self._map_severity(finding.get("severity", ""))
            if sev == Severity.INFO:
                continue
            issues.append(Issue(
                rule=finding.get("id", ""),
                severity=sev,
                message=finding.get("message", ""),
                line=finding.get("location", {}).get("line", 0),
                snippet=(finding.get("evidence", "") or "")[:80],
                category=finding.get("category", ""),
            ))
        risk = data.get("risk_assessment", {})
        score = risk.get("score", 0)
        recommendation = risk.get("recommendation", "")
        raw_meta = f"risk_score={score} recommendation={recommendation}"
        return CheckResult(
            source=self.name,
            issues=issues,
            passed=len(issues) == 0,
            raw_output=raw_meta,
        )

    @staticmethod
    def _map_severity(sev: str) -> Severity:
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.ERROR,
            "medium": Severity.WARNING,
            "low": Severity.INFO,
            "info": Severity.INFO,
        }
        return mapping.get(sev.lower(), Severity.WARNING)
