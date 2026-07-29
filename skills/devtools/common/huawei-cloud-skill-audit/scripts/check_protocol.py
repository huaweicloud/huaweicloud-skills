#!/usr/bin/env python3
"""Check protocol — unified abstractions for skill audit checks."""

from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    rule: str
    severity: Severity
    message: str
    line: int = 0
    file: str = ""
    snippet: str = ""
    category: str = ""


@dataclass
class CheckResult:
    source: str
    issues: list[Issue] = field(default_factory=list)
    passed: bool = True
    raw_output: str = ""


class ScanLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class Check:
    """Base class for all audit checks."""

    name: str = ""

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD, timeout: int = 30):
        self.scan_level = scan_level
        self.timeout = timeout

    def is_available(self) -> bool:
        """Return True if the required tool is installed and available."""
        raise NotImplementedError

    def run(self, skill_dir: Path) -> CheckResult:
        """Run check on a single skill directory."""
        raise NotImplementedError

    def run_batch(self, target: Path, skills: list[Path]) -> CheckResult:
        """Run check on multiple skills. Default: iterate and merge."""
        results = [self.run(s) for s in skills]
        all_issues = [i for r in results for i in r.issues]
        return CheckResult(
            source=self.name,
            issues=all_issues,
            passed=all(r.passed for r in results),
        )
