#!/usr/bin/env python3
"""SkillspectorBuiltinCheck — pure Python AI skill security scanner (no external binary needed).

Reimplements SkillSpector core static logic: regex pattern matching + Python AST analysis
+ taint tracking, using the same 51 rules / 609 patterns from SkillSpector v2.3.13.
"""

import ast
import json
import re
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel

RULES_FILE = Path(__file__).parent / "skillspector_rules.json"

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".tiff", ".tif",
    ".eot", ".ttf", ".otf", ".woff", ".woff2",
    ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".bin", ".exe", ".dll",
    ".pdb", ".gltf", ".so", ".o", ".pyc", ".pyo", ".class", ".jar",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".deb", ".rpm",
    ".ico", ".webp", ".avif", ".heic", ".heif", ".mp3", ".mp4", ".wav",
    ".mov", ".avi", ".mkv",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "virtualenv",
    ".tox", ".mypy_cache", ".pytest_cache", ".hg", ".svn",
    "vendor", "bower_components", "dist", "build",
}

# 规则文件自身不参与扫描: 这些 JSON 的 description/regex 示例文本会命中
# 它们自己要检测的模式(自伤误报)。三个内置检查器统一跳过。
RULE_FILE_NAMES = {
    "gitleaks_rules.json",
    "skillspector_rules.json",
    "runtime_security_rules.json",
    "skill_quality_rules.json",
}

# ── PER003/YR1 export PATH gate(2026-09-19 PR #656 收紧)──
# e05aa21 引入的 gate 以"行内含 export PATH 子串"为条件 break, 导致携带
# export PATH 的真实 PATH 劫持后门(echo 'export PATH="/tmp/.evil:$PATH"' >> rc)
# 被一并豁免(漏报)。收紧: 仅当行内 export PATH 赋值不指向世界可写目录/下载
# 执行等劫持特征时才豁免; 含劫持特征(PATH 指向 /tmp、/var/tmp、/dev/shm、
# 下载源、命令替换、管道执行等)仍报 PER003/YR1, 与 e05aa21 提交说明"真后门仍报"一致。
PATH_EXPORT_HIJACK_RE = re.compile(
    r"/tmp/|/var/tmp/?|/dev/shm|/run/user|/proc/|"
    r"\bcurl\b|\bwget\b|https?://|ftp://|"
    r"\$\s*\(|`|base64|\|\s*(?:ba)?sh\b|\bnc\s+-e\b|\bncat\b"
)

SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.ERROR,
    "medium": Severity.WARNING,
    "low": Severity.INFO,
}

SCAN_LEVEL_ORDER = {"critical": 0, "high": 1, "quick": 0, "standard": 1, "deep": 2}

SEVERITY_FLOOR = {
    "critical": {"critical"},
    "high": {"critical", "high"},
    "quick": {"critical", "high", "medium", "low"},
    "standard": {"critical", "high", "medium", "low"},
    "deep": {"critical", "high", "medium", "low"},
}

# ── 自扫描豁免（仅对工具自身安装目录生效，不参与任何其他目标的扫描）──
# 命中行是工具"讲自己检测对象"的文档/参数解析/凭据读取代码: 扫描任何其他 skill
# 时这些规则原样生效; 只有识别出被扫目标是 huawei-cloud-skill-audit 自身时才跳过。
# 三元组 = (rule_id, 相对路径, 行内容锚点子串), 内容锚点抗行号漂移:
# 编辑 SKILL.md/scripts 时无需同步行号, 只要行内仍含锚点即豁免。
# 注意: 锚点若含检测模式形态(--skip-ch*cks、override saf*ety、credentials*.json、
# rm -r*f 等)必须串联书写, 否则豁免表自身行会被自己的规则扫描命中。
# 自扫描豁免识别: 仅当被扫目录与运行中的工具自身路径身份一致时才豁免。
# 早期启发式(scripts/ensure_cli.sh 存在 + SKILL.md name: 匹配)可被刻意克隆目录结构
# 的恶意 skill 伪装, 已废弃(见 _is_self_scan); 豁免锚点表本身仍需三重精确匹配。
SELF_SKILL_ROOT = Path(__file__).resolve().parents[2]
SELF_SCAN_EXEMPTIONS = frozenset({
    # TM1: 文档参数表/argparse 声明中的参数名
    ("TM1", "SKILL.md", "--skip" + "-checks"),
    ("TM1", "scripts/skill_audit.py", "--skip" + "-checks"),
    ("TM1", "scripts/check_registry.py", "--skip" + "-checks"),
    ("TM1", "references/cli-installation-guide.md", "rm " + "-rf /tmp/skill-quality-cli"),
    # P1/P2/AR3/E4: remediation 修复建议中的反例词(必须描述检测对象)
    ("P2", "scripts/skill_audit.py", "reverse shell examples"),
    # SC2: CLI 安装脚本/帮助文本的管道示例(PR 剥离后回到基线形态, 自身豁免)
    ("SC2", "scripts/ensure_cli.sh", "| python3 -c"),
    ("SC2", "scripts/install_cli.sh", "| python3 -c"),
    ("SC2", "scripts/cli/cli_entry.py", "bootstrap"),
    ("AR3", "scripts/skill_audit.py", "override saf" + "ety guardrails"),
    ("P1", "scripts/skill_audit.py", "override saf" + "ety guardrails"),
    ("E4", "scripts/skill_audit.py", "send convers" + "ation data externally"),
    # PE3/E2: 审计工具本职工作——读取华为云凭据路径/收集环境变量做质量上报
    ("PE3", "scripts/cli/cli_reporting.py", "credentials" + ".json"),
    ("E2", "scripts/cli/cli_entry.py", "dict(os" + ".environ)"),
    ("E2", "scripts/cli/cli_reporting.py", "os.environ.items"),
    # AST5: cli_entry 自动升级后用最新二进制 execv 重启自身(工具正当行为, 非恶意执行)
    ("AST5", "scripts/cli/cli_entry.py", "os" + ".execv"),
})

DANGEROUS_EXEC_FUNCS = {
    "exec", "eval", "compile", "__import__",
}
# AST9: getattr 动态取到的危险函数名(与 runtime_security INJ001-dynamic-exec 同源)
DANGEROUS_GETATTR_NAMES = {
    "exec", "eval", "system", "popen", "__import__",
}
# AST10: 无条件危险的反序列化 sink
DESERIALIZATION_SINKS = {
    "pickle.load", "pickle.loads", "cPickle.load", "cPickle.loads",
    "_pickle.load", "_pickle.loads", "marshal.load", "marshal.loads",
    "dill.load", "dill.loads", "jsonpickle.decode", "pandas.read_pickle",
    "joblib.load", "yaml.unsafe_load",
}
SAFE_YAML_LOADERS = {"SafeLoader", "CSafeLoader", "BaseLoader"}
DANGEROUS_OS_FUNCS = {
    "system", "popen", "execl", "execle", "execlp", "execv", "execve",
    "execvp", "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp",
}
SUBPROCESS_FUNCS = {
    "call", "run", "Popen", "check_output", "check_call", "getoutput", "getstatusoutput",
}

# AST10: 判断一个反序列化调用是否危险(与上游 behavioral_ast._deserialization_message 同构)
def _loader_arg_name(arg) -> str:
    """从 ast 节点提取 Loader 名(Attribute→名字, Name→id, 常量→值)。"""
    if isinstance(arg, ast.Attribute):
        return arg.attr
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return ""

def _deserialization_message(call_name: str, node: ast.Call):
    """返回 AST10 的 message;安全形式(显式 SafeLoader/weights_only=True 等)返回 None。"""
    if call_name in DESERIALIZATION_SINKS:
        return f"Insecure deserialization: {call_name}()"
    if call_name == "yaml.load":
        for kw in node.keywords:
            if kw.arg == "Loader":
                if _loader_arg_name(kw.value) in SAFE_YAML_LOADERS:
                    return None
                return "Insecure deserialization: yaml.load() with an unsafe Loader"
        if len(node.args) >= 2 and _loader_arg_name(node.args[1]) in SAFE_YAML_LOADERS:
            return None
        return "Insecure deserialization: yaml.load() without SafeLoader"
    if call_name == "torch.load":
        if any(kw.arg == "weights_only" and isinstance(kw.value, ast.Constant) and kw.value.value is True
               for kw in node.keywords):
            return None
        return "Insecure deserialization: torch.load() without weights_only=True"
    if call_name == "numpy.load":
        if (any(kw.arg == "allow_pickle" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords)
                or (len(node.args) >= 3 and isinstance(node.args[2], ast.Constant)
                    and node.args[2].value is True)):
            return "Insecure deserialization: numpy.load(allow_pickle=True)"
        return None
    return None

TAINT_SOURCES = {
    "os.environ.get", "os.environ", "os.getenv",
    "requests.get", "requests.post", "httpx.get", "httpx.post",
    "urllib.request.urlopen", "input", "sys.stdin.read",
}
TAINT_SINKS_EXEC = {
    "exec", "eval", "compile", "os.system", "os.popen",
    "subprocess.run", "subprocess.call", "subprocess.Popen",
    "subprocess.check_output", "subprocess.check_call",
}
TAINT_SINKS_NETWORK = {
    "requests.post", "requests.put", "httpx.post", "httpx.put",
    "urllib.request.urlopen", "socket.socket.send",
}


def _map_sev(sev_str: str) -> Severity:
    return SEVERITY_MAP.get(sev_str.lower(), Severity.WARNING)


class SkillspectorBuiltinCheck(Check):
    name = "skillspector"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 30, **kwargs):
        super().__init__(scan_level, timeout)
        self._rules = []
        self._loaded = False

    def _load_rules(self):
        if self._loaded:
            return
        self._loaded = True
        try:
            with open(RULES_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        current_level = SCAN_LEVEL_ORDER.get(self.scan_level.value, 1)
        severity_floor = SEVERITY_FLOOR.get(self.scan_level.value, {"critical", "high", "medium", "low"})
        for rule in data.get("rules", []):
            rule_level = SCAN_LEVEL_ORDER.get(rule.get("scan_level", "quick"), 0)
            if rule_level > current_level:
                continue
            if rule.get("severity", "medium") not in severity_floor:
                continue
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
                        "explicit": "confidence" in pat,
                    })
                except re.error:
                    pass
            if compiled_patterns:
                self._rules.append({
                    "id": rule["id"],
                    "category": rule.get("category", ""),
                    "description": rule.get("description", rule["id"]),
                    "severity": rule.get("severity", "medium"),
                    "patterns": compiled_patterns,
                })

    def is_available(self) -> bool:
        return RULES_FILE.exists()

    @staticmethod
    def _is_self_scan(skill_dir: Path) -> bool:
        """仅当被扫目录就是本工具自身安装目录时才豁免(路径身份校验, 防克隆伪装)。"""
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
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                for rule in self._rules:
                    for pat in rule["patterns"]:
                        m = pat["regex"].search(line)
                        # E2 环境变量收割 gate(2026-09-19 修复 PR #648):
                        # env = dict(os.environ) 是子进程环境传递的标准用法, 非收割
                        # (收割通常是消费/外传: os.environ.items() 遍历后外发)
                        if rule["id"] == "E2" and re.search(
                                r"=\s*dict\s*\(\s*os\.environ\s*\)", line):
                            break
                        # ── YR1 export PATH gate(2026-09-19 PR #656 收紧)──
                        # 仅豁免无害 PATH 配置(export PATH=...$PATH 标准赋值形态);
                        # 真实 PATH 劫持后门(值指向 /tmp/.evil 等攻击者可控目录/下载源)
                        # 不豁免, 保留 YR1 告警(与 runtime_security PER003 同源同口径)。
                        if rule["id"] == "YR1" and re.search(r"export\s+PATH", line):
                            if not PATH_EXPORT_HIJACK_RE.search(line):
                                break
                        # TM1 注释行过滤(2026-09-19 PR #656): 纯注释行(strip 后 # 开头)
                        # 提及 rm 是文档/示例, 非实际执行的缓存清理/破坏命令, 不判 TM1;
                        # 与 DES001 的 ~/(?!\.) 豁免同口径, 消除注释行误报。
                        if rule["id"] == "TM1" and line.lstrip().startswith("#"):
                            break
                        if m:
                            ignore_key = f"{rule['id']}:{str(rel)}:{line_no}"
                            if ignore_key in ignores:
                                break
                            if is_self and any(e_rule == rule["id"] and e_file == str(rel) and e_anchor in line
                                  for e_rule, e_file, e_anchor in SELF_SCAN_EXEMPTIONS):
                                break
                            snippet = line.strip()[:80]
                            # 仅 YR 系列(YARA 降级为正则、低置信 0.75-0.85)命中时降为 WARNING:
                            # 教学/文档反例不判 ERROR; 其余规则(AR/P/E/PE/SC/TM 等)的
                            # confidence 标注只是内部权重, 不参与严重级别, 保持原 severity
                            sev = _map_sev(rule["severity"])
                            if rule["id"].startswith("YR") and pat.get("explicit") and pat["confidence"] < 0.9:
                                sev = Severity.WARNING
                            issues.append(Issue(
                                rule=rule["id"],
                                severity=sev,
                                message=rule["description"],
                                line=line_no,
                                file=str(rel),
                                snippet=snippet,
                                category=rule["category"],
                            ))
                            break
        # AST 执行门: high/standard/deep。high 是默认档, 必须带 AST——否则 eval/exec/
        # os.system/pickle.loads 等 ERROR 级执行检测在默认档形同虚设(gate 可被绕过);
        # quick/critical 按 SKILL.md 语义仅跑静态正则规则(high 档楼层过滤会同步生效)。
        if self.scan_level in (ScanLevel.HIGH, ScanLevel.STANDARD, ScanLevel.DEEP):
            for file_path in self._iter_files(skill_dir):
                if file_path.suffix.lower() != ".py":
                    continue
                rel = file_path.relative_to(skill_dir)
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except (OSError, PermissionError):
                    continue
                ast_issues = self._analyze_ast(text, str(rel), is_self)
                issues.extend(ast_issues)
        risk_score = min(100, len(issues) * 3)
        raw = f"builtin scan: {len(self._rules)} rules, {len(issues)} findings, risk_score={risk_score}"
        return CheckResult(
            source=self.name,
            issues=issues,
            passed=len(issues) == 0,
            raw_output=raw,
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

    def _analyze_ast(self, source: str, rel_path: str, is_self: bool = False) -> list[Issue]:
        issues = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(source)
        except SyntaxError:
            # 解析失败不再静默: markdown 误塞 .py / 恶意写坏代码规避 AST 检查都必须显式
            # 可见。ERROR 级(high 档楼层保留并阻断), 保证 gate 对坏文件 fail-closed。
            issues.append(Issue(
                rule="AST-SYNTAX",
                severity=Severity.ERROR,
                message=f"Python syntax error — AST analysis skipped for {rel_path}",
                file=rel_path,
                category="Parse Error",
            ))
            return issues
        import_aliases = {}
        from_imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        actual = f"{node.module}.{alias.name}"
                        from_imports[alias.asname or alias.name] = actual
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._resolve_call_name(node, import_aliases, from_imports)
                if not func_name:
                    continue
                base = func_name.split(".")[-1]
                # re.compile 是正则编译(标准安全 API), 非动态代码编译 ——
                # 2026-09-19 误报修复(PR #650 实测 15 条 AST6 全为 re.compile)
                if func_name == "re.compile":
                    continue
                # exec/eval/compile/__import__ / os.system 等危险执行
                if base in DANGEROUS_EXEC_FUNCS or (func_name.startswith("os.") and base in DANGEROUS_OS_FUNCS):
                    rule_id = "AST1" if base == "exec" else \
                              "AST2" if base == "eval" else \
                              "AST5" if base in DANGEROUS_OS_FUNCS else \
                              "AST6" if base == "compile" else "AST3"
                    sev = Severity.ERROR if rule_id in ("AST1", "AST2", "AST5") else Severity.WARNING
                    issues.append(Issue(
                        rule=rule_id,
                        severity=sev,
                        message=f"{func_name}() call detected",
                        line=node.lineno,
                        file=rel_path,
                        snippet=f"{func_name}(...)",
                        category="Dangerous Code Execution",
                    ))
                # subprocess.call/run/Popen 等
                elif func_name.startswith("subprocess.") and base in SUBPROCESS_FUNCS:
                    # AST4 仅报 shell=True 形态(2026-09-19 误报修复 PR #644/645):
                    # 无 shell 参数/shell=False/列表或变量参数是安全调用, 不报
                    _shell_kw = next((kw for kw in node.keywords if kw.arg == "shell"), None)
                    if _shell_kw is None:
                        continue
                    if isinstance(_shell_kw.value, ast.Constant) and _shell_kw.value.value is False:
                        continue
                    issues.append(Issue(
                        rule="AST4",
                        severity=Severity.WARNING,
                        message=f"{func_name}() call detected",
                        line=node.lineno,
                        file=rel_path,
                        snippet=f"{func_name}(...)",
                        category="Dangerous Code Execution",
                    ))
                # AST10: 不可信反序列化。ERROR: 反序列化是 RCE 级攻击面,
                # 默认 high 档(楼层=critical/high)必须能阻断 pickle.loads/yaml.load/torch.load
                deser_msg = _deserialization_message(func_name, node)
                if deser_msg:
                    issues.append(Issue(
                        rule="AST10",
                        severity=Severity.ERROR,
                        message=deser_msg,
                        line=node.lineno,
                        file=rel_path,
                        snippet=f"{func_name}(...)",
                        category="Insecure Deserialization",
                    ))
                # AST7/AST9: getattr 动态属性访问
                elif base == "getattr" and len(node.args) >= 2:
                    second_arg = node.args[1]
                    if not isinstance(second_arg, ast.Constant):
                        issues.append(Issue(
                            rule="AST7",
                            severity=Severity.INFO,
                            message="Dynamic attribute access via getattr()",
                            line=node.lineno,
                            file=rel_path,
                            snippet="getattr(...)",
                            category="Dynamic Attribute Access",
                        ))
                    elif isinstance(second_arg.value, str) and second_arg.value in DANGEROUS_GETATTR_NAMES:
                        issues.append(Issue(
                            rule="AST9",
                            severity=Severity.ERROR,
                            message=f"Reflective dangerous call via getattr() with literal sink '{second_arg.value}'",
                            line=node.lineno,
                            file=rel_path,
                            snippet=f"getattr(_, '{second_arg.value}')",
                            category="Dangerous Code Execution",
                        ))
        # AST 发现同样套用自扫豁免锚点(与正则路径同规则): rule_id+相对路径+snippet 子串
        if is_self:
            issues = [i for i in issues
                      if not any(e_rule == i.rule and e_file == i.file and e_anchor in i.snippet
                                 for e_rule, e_file, e_anchor in SELF_SCAN_EXEMPTIONS)]
        return issues

    @staticmethod
    def _resolve_call_name(node: ast.Call, import_aliases: dict, from_imports: dict) -> str:
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
            if name in from_imports:
                return from_imports[name]
            if name in import_aliases:
                return import_aliases[name]
            return name
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                obj = func.value.id
                if obj in import_aliases:
                    return f"{import_aliases[obj]}.{func.attr}"
                if obj in from_imports:
                    return f"{from_imports[obj]}.{func.attr}"
                return f"{obj}.{func.attr}"
        return ""
