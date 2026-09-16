#!/usr/bin/env python3
"""RuntimeSecurityCheck — CWE 高危运行模式扫描器(不受 scan_level floor 限制)。

与 skillspector/gitleaks 的区别: 这两个内置扫描器在 scan_level=high 下只执行
critical/error 级规则(warning/info 被 SEVERITY_FLOOR 过滤), 且所有级别都不执行
low(info) 级规则。RuntimeSecurityCheck 是级别无关检查器: 规则全部执行,
每条规则自带 severity(按审计标准表), 由调用方决定阻断语义
(critical/error 阻断, warning/info 提示)。

规则来源: 两个文件(多文件支持, 2026-09-14)——
runtime_security_rules.json(11 条 CWE 高危模式: CWE-913 间接执行/导入钩子劫持、
CWE-78 命令注入、CWE-502 YAML 反序列化、CWE-522 凭据窃取、CWE-749 沙箱逃逸、
CWE-1106 依赖仿冒、CWE-327 混淆、CWE-506 逻辑炸弹、CWE-74 环境变量注入) +
skill_quality_rules.json(3 条人工评审归纳质量规则: Q001 本机路径硬编码 / Q002 32hex
ProjectID / Q003 configure set 凭据命令, 全 warning)。
注意: 规则文件必须放在 checks/ 根目录而非 checks/rules/(skillspector 的加载器
遍历 rules/ 下所有 json, 放进去会被 skillspector 双份执行 —— 2026-09-14 实测);
RULES_FILES 用显式列表而不 glob(会抓到 gitleaks_rules.json)。
"""

import json
import re
import warnings
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity
from checks.skillspector_builtin_check import BINARY_EXTENSIONS, SKIP_DIRS

RULES_FILES = [
    Path(__file__).parent / "runtime_security_rules.json",
    Path(__file__).parent / "skill_quality_rules.json",
]

# rule 文件 severity 字符串 → 协议 Severity(与 skillspector SEVERITY_MAP 同口径)
_RULE_SEVERITY = {
    "critical": Severity.CRITICAL,
    "high": Severity.ERROR,
    "medium": Severity.WARNING,
    "low": Severity.INFO,
}


class RuntimeSecurityCheck(Check):
    """逐行规则匹配的 CWE 高危模式检查器, 所有规则无条件执行。"""

    name = "runtime_security"

    def __init__(self, scan_level=None, timeout: int = 30, **kwargs):
        super().__init__(scan_level, timeout)
        self._rules = []
        self._loaded = False

    def _load_rules(self):
        if self._loaded:
            return
        self._loaded = True
        for rules_file in RULES_FILES:
            if not rules_file.is_file():
                continue
            try:
                data = json.loads(rules_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for rule in data.get("rules", []):
                compiled_patterns = []
                for pat in rule.get("patterns", []):
                    regex_str = pat.get("regex", "")
                    if not regex_str:
                        continue
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", (FutureWarning, DeprecationWarning))
                            compiled = re.compile(regex_str)
                        compiled_patterns.append({
                            "regex": compiled,
                            "confidence": pat.get("confidence", 0.7),
                        })
                    except re.error:
                        continue
                if compiled_patterns:
                    self._rules.append({
                        "id": rule["id"],
                        "category": rule.get("category", ""),
                        "description": rule.get("description", rule["id"]),
                        "severity": _RULE_SEVERITY.get(rule.get("severity", "medium"),
                                                       Severity.WARNING),
                        "patterns": compiled_patterns,
                    })

    def is_available(self) -> bool:
        return any(f.is_file() for f in RULES_FILES)

    def run(self, skill_dir: Path) -> CheckResult:
        self._load_rules()
        if not self._rules:
            return CheckResult(source=self.name, passed=True, raw_output="No rules loaded")
        ignores = self._load_skillspectorignore(skill_dir)
        issues = []
        for file_path in self._iter_files(skill_dir):
            rel = file_path.relative_to(skill_dir)
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, PermissionError):
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                for rule in self._rules:
                    for pat in rule["patterns"]:
                        m = pat["regex"].search(line)
                        if m:
                            ignore_key = f"{rule['id']}:{str(rel)}:{line_no}"
                            if ignore_key in ignores:
                                break
                            issues.append(Issue(
                                rule=rule["id"],
                                severity=rule["severity"],
                                message=rule["description"],
                                line=line_no,
                                file=str(rel),
                                snippet=line.strip()[:80],
                                category=rule["category"],
                            ))
                            break
        return CheckResult(
            source=self.name,
            issues=issues,
            passed=len(issues) == 0,
            raw_output=f"runtime_security: {len(self._rules)} rules, {len(issues)} findings",
        )

    def _iter_files(self, skill_dir: Path):
        for p in skill_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() not in BINARY_EXTENSIONS:
                if p.name in {".gitleaksignore", ".skillspectorignore"}:
                    continue
                if not any(part in SKIP_DIRS for part in p.parts):
                    yield p

    @staticmethod
    def _load_skillspectorignore(skill_dir: Path) -> set[str]:
        ignore_file = skill_dir / ".skillspectorignore"
        if not ignore_file.exists():
            return set()
        try:
            with open(ignore_file, encoding="utf-8") as f:
                data = json.load(f)
            return set(data.keys())
        except (json.JSONDecodeError, OSError):
            return set()