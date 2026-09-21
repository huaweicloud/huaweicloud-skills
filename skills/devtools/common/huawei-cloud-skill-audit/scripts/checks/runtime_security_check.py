#!/usr/bin/env python3
"""RuntimeSecurityCheck — CWE 高危运行模式扫描器(不受 scan_level floor 限制)。

与 skillspector/gitleaks 的区别: 这两个内置扫描器在 scan_level=high 下只执行
critical/error 级规则(warning/info 被 SEVERITY_FLOOR 过滤), 且所有级别都不执行
low(info) 级规则。RuntimeSecurityCheck 是级别无关检查器: 规则全部执行,
每条规则自带 severity(按审计标准表), 由调用方决定阻断语义
(critical/error 阻断, warning/info 提示)。

规则来源: 两个文件(多文件支持, 2026-09-14)——
runtime_security_rules.json(36 条 CWE 高危模式: CWE-913 间接执行/导入钩子劫持、
CWE-78 命令注入、CWE-502 YAML 反序列化、CWE-522 凭据窃取、CWE-749 沙箱逃逸、
CWE-1106 依赖仿冒、CWE-327 混淆、CWE-506 逻辑炸弹、CWE-74 环境变量注入、
CWE-287 持久化/后门、CWE-404 破坏性操作、CWE-400 资源滥用/挖矿、CWE-732 权限控制) +
skill_quality_rules.json(3 条人工评审归纳质量规则: Q001 本机路径硬编码 / Q002 32hex
ProjectID / Q003 configure set 凭据命令, 全 critical)。
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
from checks.skillspector_builtin_check import (
    BINARY_EXTENSIONS,
    SKIP_DIRS,
    RULE_FILE_NAMES,
    SELF_SKILL_ROOT,
    PATH_EXPORT_HIJACK_RE,
)

# 自扫描豁免(与 skillspector 对称): 仅对工具自身安装目录生效, 不影响任何其他目标。
# 当前自身文档/代码无触发行, 表为空; 未来若 SKILL.md/references 出现 Q001-Q003 或
# CWE 模式示例, 在此登记 (rule_id, rel_path, 行内容锚点子串)。
SELF_SCAN_EXEMPTIONS = frozenset()

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
        is_self = self._is_self_scan(skill_dir)
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
                            # PER003 排除 PATH 配置(2026-09-19 修复 PR #648,
                            # PR #656 收紧): 安装脚本向 ~/.bashrc 追加 export PATH
                            # 是标准行为, 非自启动持久化; 但真实 PATH 劫持后门
                            # (export PATH 指向 /tmp/.evil 等攻击者可控目录/下载源)
                            # 不豁免, 保留 PER003 告警。
                            if rule["id"].startswith("PER003") and re.search(
                                    r"export\s+PATH", line):
                                if not PATH_EXPORT_HIJACK_RE.search(line):
                                    break
                            # INT002 写入形态 gating(2026-09-19 误报修复 PR #650,
                            # PR #656 补漏): 检查/引用形态(grep、[[ -f、2>/dev/null、
                            # local 赋值、test)只是读取/判断 agent 记忆配置, 非篡改
                            # 写入; 真实写入(echo >/write_text/os.remove/重定向到
                            # ~/.hermes 等)仍命中; 带 2>/dev/null 的重定向写入不豁免。
                            if rule["id"].startswith("INT002"):
                                _int002_write = re.search(
                                    r"(?:>>|>)\s*[^|&;\n]*?(?:~?/\.hermes|~?/\.openclaw|SOUL\.md|IDENTITY\.md)\b",
                                    line)
                                if _int002_write:
                                    pass  # 真实写入形态 → 不 gate, 继续命中
                                elif re.search(
                                        r"grep\b|\[\[ -f|2>/dev/null|\blocal\s+\w+\s*=|test\b",
                                        line):
                                    break
                            ignore_key = f"{rule['id']}:{str(rel)}:{line_no}"
                            if ignore_key in ignores:
                                break
                            if is_self and any(e_rule == rule["id"] and e_file == str(rel) and e_anchor in line
                                  for e_rule, e_file, e_anchor in SELF_SCAN_EXEMPTIONS):
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
                if p.name in RULE_FILE_NAMES:
                    continue
                if not any(part in SKIP_DIRS for part in p.parts):
                    yield p

    @staticmethod
    def _is_self_scan(skill_dir: Path) -> bool:
        """仅当被扫目录就是本工具自身安装目录时才豁免(与 skillspector 同路径身份校验)。"""
        try:
            return Path(skill_dir).resolve() == SELF_SKILL_ROOT
        except OSError:
            return False

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