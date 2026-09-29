#!/usr/bin/env python3
"""Check protocol — unified abstractions for skill audit checks."""

import concurrent.futures
import re
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


# 三引号字符串(docstring)内的行号集合(1-based)。2026-09-28 PR #738 下沉:
# 模块 docstring 的说明文本提及 keyring/token 等安全词是文档, 非真实调用。
# 实用状态机: 打开行 = 行首三引号(模块/函数 docstring 均在行首或缩进后, 正则/
# 字符串字面量中间的三引号不误开); 闭合行 = 后续出现同款定界符(该行也计入);
# 同行开闭(行首 \"\"\"...\"\"\")= 单行 docstring → 豁免该行, 状态不变。
def docstring_lines(text: str) -> set:
    lines = text.splitlines()
    res = set()
    in_doc = None
    for i, ln in enumerate(lines, 1):
        if in_doc is None:
            m = re.search(r'^\s*"""|^\s*\'\'\'', ln)
            if m:
                delim = m.group(0).lstrip()
                if ln.count(delim) >= 2:
                    # 同行开闭: 单行 docstring(文档语境) → 豁免该行
                    res.add(i)
                    continue
                in_doc = delim
                res.add(i)
        else:
            res.add(i)
            if in_doc in ln:
                in_doc = None
    return res


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
    skill: str = ""


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
        """Run check on multiple skills with per-skill isolation and timeout.

        - 单 skill 抛异常不再中断整批: 产出显式 CHECK-ERR issue 后继续剩余 skill
        - 每 skill 限时 self.timeout 秒(线程限时): 恶意正则/巨树最多拖慢一个 skill 的
          预算, 不会拖垮整个 gate; 到期线程无法强杀, 但结果已按 TIMEOUT 处理并继续
        """
        budget = self.timeout if self.timeout and self.timeout > 0 else 30
        all_issues = []
        passed = True
        for s in skills:
            try:
                if budget:
                    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    try:
                        r = ex.submit(self.run, s).result(timeout=budget)
                    except concurrent.futures.TimeoutError:
                        all_issues.append(Issue(
                            rule="TIMEOUT",
                            severity=Severity.WARNING,
                            message=f"{self.name}: exceeded {budget}s on {s.name}, result skipped",
                            file=s.name, skill=s.name, category="Timeout",
                        ))
                        continue
                    finally:
                        ex.shutdown(wait=False)
                else:
                    r = self.run(s)
            except Exception as e:  # noqa: BLE001 — 逐 skill 隔离
                all_issues.append(Issue(
                    rule="CHECK-ERR",
                    severity=Severity.WARNING,
                    message=f"{self.name}: crashed on {s.name}: {e!r}",
                    file=s.name, skill=s.name, category="RuntimeError",
                ))
                continue
            for i in r.issues:
                i.skill = i.skill or s.name
                all_issues.append(i)
            passed = passed and r.passed
        return CheckResult(
            source=self.name,
            issues=all_issues,
            passed=passed,
        )
