#!/usr/bin/env python3
"""GitleaksBuiltinCheck — pure Python credential leak detection (no external binary needed).

Reimplements gitleaks core logic: regex pattern matching + Shannon entropy scoring
+ keyword pre-filtering + allowlist exclusion, using the same 222 rules from gitleaks v8.30.1.
"""

import json
import math
import re
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel

RULES_FILE = Path(__file__).parent / "gitleaks_rules.json"

GITLEAKS_SEVERITY_FLOOR = {
    "critical": {"critical", "high"},
    "high": {"critical", "high"},
    "quick": {"critical", "high", "warning"},
    "standard": {"critical", "high", "warning"},
    "deep": {"critical", "high", "warning"},
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".tiff", ".tif",
    ".eot", ".ttf", ".otf", ".woff", ".woff2",
    ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".bin", ".exe", ".dll",
    ".pdb", ".gltf", ".so", ".o", ".pyc", ".pyo", ".class", ".jar",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".deb", ".rpm",
    ".ico", ".webp", ".avif", ".heic", ".heif", ".mp3", ".mp4", ".wav",
    ".mov", ".avi", ".mkv", ".woff2",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "virtualenv",
    ".tox", ".mypy_cache", ".pytest_cache", ".hg", ".svn",
    "vendor", "bower_components", "dist", "build",
}


def _shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    freq = {}
    for c in data:
        freq[c] = freq.get(c, 0) + 1
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def _compile_global_allowlist(global_allow: dict) -> list[re.Pattern]:
    patterns = []
    for r in global_allow.get("paths", []):
        try:
            patterns.append(re.compile(r))
        except re.error:
            pass
    return patterns


def _compile_global_regex_allowlist(global_allow: dict) -> list[re.Pattern]:
    patterns = []
    for r in global_allow.get("regexes", []):
        try:
            patterns.append(re.compile(r))
        except re.error:
            pass
    return patterns


class GitleaksBuiltinCheck(Check):
    name = "gitleaks"

    def __init__(self, scan_level: ScanLevel = ScanLevel.STANDARD,
                 timeout: int = 30, **kwargs):
        super().__init__(scan_level, timeout)
        self._rules = []
        self._global_path_allowlist = []
        self._global_regex_allowlist = []
        self._global_stopwords = []
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
        severity_floor = GITLEAKS_SEVERITY_FLOOR.get(self.scan_level.value, {"critical", "high", "warning"})
        self._global_path_allowlist = _compile_global_allowlist(data.get("global_allowlist", {}))
        self._global_regex_allowlist = _compile_global_regex_allowlist(data.get("global_allowlist", {}))
        self._global_stopwords = data.get("global_allowlist", {}).get("stopwords", [])
        sev_map = {"critical": Severity.CRITICAL, "high": Severity.ERROR, "warning": Severity.WARNING}
        for rule in data.get("rules", []):
            rule_sev = rule.get("severity", "high")
            if rule_sev not in severity_floor:
                continue
            regex_str = rule.get("regex")
            if not regex_str:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    compiled = re.compile(regex_str)
                self._rules.append({
                    "id": rule["id"],
                    "description": rule.get("description", rule["id"]),
                    "regex": compiled,
                    "entropy": rule.get("entropy"),
                    "keywords": rule.get("keywords", []),
                    "severity": sev_map.get(rule_sev, Severity.ERROR),
                })
            except re.error:
                pass

    def is_available(self) -> bool:
        return RULES_FILE.exists()

    @staticmethod
    def _load_gitleaksignore(skill_dir: Path) -> set[str]:
        ignore_file = skill_dir / ".gitleaksignore"
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
        ignores = self._load_gitleaksignore(skill_dir)
        issues = []
        for file_path in self._iter_files(skill_dir):
            rel = file_path.relative_to(skill_dir)
            if self._is_path_allowed(rel):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, PermissionError):
                continue
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                if self._is_line_allowed(line):
                    continue
                for rule in self._rules:
                    if rule["keywords"] and not any(kw in line.lower() for kw in rule["keywords"]):
                        continue
                    for m in rule["regex"].finditer(line):
                        match_str = m.group(0)
                        if self._is_match_allowed(match_str):
                            continue
                        if rule["entropy"] is not None:
                            groups = [g for g in m.groups() if g]
                            target = groups[0] if groups else match_str
                            if _shannon_entropy(target) < rule["entropy"]:
                                continue
                        ignore_key = f"{rule['id']}:{str(rel)}:{line_no}"
                        if ignore_key in ignores:
                            continue
                        snippet = match_str[:80] + "..." if len(match_str) > 80 else match_str
                        issues.append(Issue(
                            rule=rule["id"],
                            severity=rule["severity"],
                            message=rule["description"],
                            line=line_no,
                            file=str(rel),
                            snippet=snippet,
                            category=rule["id"],
                        ))
                        break
        ignored_count = len(ignores)
        raw = f"builtin scan: {len(self._rules)} rules, {len(issues)} findings, {ignored_count} ignored"
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
                if not any(part in SKIP_DIRS for part in p.parts):
                    yield p

    def _is_path_allowed(self, rel_path: Path) -> bool:
        rel_str = str(rel_path)
        for pat in self._global_path_allowlist:
            if pat.search(rel_str):
                return True
        return False

    def _is_line_allowed(self, line: str) -> bool:
        stripped = line.strip()
        for pat in self._global_regex_allowlist:
            if pat.fullmatch(stripped):
                return True
        return False

    def _is_match_allowed(self, match_str: str) -> bool:
        lower = match_str.lower()
        for sw in self._global_stopwords:
            if sw in lower:
                return True
        return False
