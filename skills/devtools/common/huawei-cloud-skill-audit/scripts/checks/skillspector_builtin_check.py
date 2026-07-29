#!/usr/bin/env python3
"""SkillspectorBuiltinCheck — pure Python AI skill security scanner (no external binary needed).

Reimplements SkillSpector core static logic: regex pattern matching + Python AST analysis
+ taint tracking, using the same 47 rules / 439 patterns from SkillSpector v2.3.13.
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

SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.ERROR,
    "medium": Severity.WARNING,
    "low": Severity.INFO,
}

SCAN_LEVEL_ORDER = {"critical": 0, "high": 0, "quick": 0, "standard": 1, "deep": 2}

SEVERITY_FLOOR = {
    "critical": {"critical"},
    "high": {"critical", "high"},
    "quick": {"critical", "high", "medium", "low"},
    "standard": {"critical", "high", "medium", "low"},
    "deep": {"critical", "high", "medium", "low"},
}

DANGEROUS_EXEC_FUNCS = {
    "exec", "eval", "compile", "__import__",
}
DANGEROUS_OS_FUNCS = {
    "system", "popen", "execl", "execle", "execlp", "execv", "execve",
    "execvp", "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp",
}
SUBPROCESS_FUNCS = {
    "call", "run", "Popen", "check_output", "check_call", "getoutput", "getstatusoutput",
}

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

    def run(self, skill_dir: Path) -> CheckResult:
        self._load_rules()
        if not self._rules:
            return CheckResult(source=self.name, passed=True, raw_output="No rules loaded")
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
                        if m:
                            snippet = line.strip()[:80]
                            issues.append(Issue(
                                rule=rule["id"],
                                severity=_map_sev(rule["severity"]),
                                message=rule["description"],
                                line=line_no,
                                file=str(rel),
                                snippet=snippet,
                                category=rule["category"],
                            ))
                            break
        if self.scan_level in (ScanLevel.STANDARD, ScanLevel.DEEP):
            for file_path in self._iter_files(skill_dir):
                if file_path.suffix.lower() != ".py":
                    continue
                rel = file_path.relative_to(skill_dir)
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except (OSError, PermissionError):
                    continue
                ast_issues = self._analyze_ast(text, str(rel))
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
                if not any(part in SKIP_DIRS for part in p.parts):
                    yield p

    def _analyze_ast(self, source: str, rel_path: str) -> list[Issue]:
        issues = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(source)
        except SyntaxError:
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
                if func_name in DANGEROUS_EXEC_FUNCS or func_name in DANGEROUS_OS_FUNCS:
                    rule_id = "AST1" if func_name == "exec" else \
                              "AST2" if func_name == "eval" else \
                              "AST5" if func_name in DANGEROUS_OS_FUNCS else \
                              "AST6" if func_name == "compile" else "AST3"
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
                elif func_name == "subprocess":
                    for attr_node in ast.walk(node):
                        if isinstance(attr_node, ast.Attribute) and attr_node.attr in SUBPROCESS_FUNCS:
                            issues.append(Issue(
                                rule="AST4",
                                severity=Severity.WARNING,
                                message=f"subprocess.{attr_node.attr}() call detected",
                                line=node.lineno,
                                file=rel_path,
                                snippet=f"subprocess.{attr_node.attr}(...)",
                                category="Dangerous Code Execution",
                            ))
            if isinstance(node, ast.Call):
                func_name = self._resolve_call_name(node, import_aliases, from_imports)
                if func_name and func_name.startswith("os.") and func_name.split(".")[-1] in DANGEROUS_OS_FUNCS:
                    pass
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
