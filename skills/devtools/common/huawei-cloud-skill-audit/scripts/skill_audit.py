#!/usr/bin/env python3
"""Skill Targeted Audit — skillcheck + markdownlint-cli2 + skillspector + hwcloud-spec + gitleaks"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check_protocol import Check, CheckResult, Issue, Severity, ScanLevel
from check_registry import AuditConfig, create_checks, resolve_enabled_checks

# ── CLI ──

def parse_args():
    p = argparse.ArgumentParser(description="Skill gate audit")
    p.add_argument("--target", required=True, help="Single skill dir or parent folder of skills")
    p.add_argument("--output-dir", default=None, help="Report output dir (default: parent of target)")
    p.add_argument("--scan-level", default="critical",
                    choices=["critical", "high", "quick", "standard", "deep"],
                    help="Scan depth: critical(CRITICAL only), high(CRITICAL+ERROR), quick(+patterns), standard(+AST+taint), deep(+MCP)")
    p.add_argument("--checks", default=None,
                    help="Comma-separated checks to run (default: all). "
                         "Available: skillspector,gitleaks")
    p.add_argument("--skip-checks", default=None,
                   help="Comma-separated checks to skip")
    p.add_argument("--skillspector", default="", help="SkillSpector binary path override")
    p.add_argument("--gitleaks", default="", help="gitleaks binary path override")
    p.add_argument("--node-bin", default="", help="Node bin dir for npx (e.g. /opt/nvm/versions/node/v18.20.8/bin)")
    p.add_argument("--no-install", action="store_true", help="Skip auto-install of tools")
    return p.parse_args()

# ── Auto-install ──

SEVERITY_FLOOR_MAP = {
    "critical": {"critical"},
    "high": {"critical", "error"},
}


def _get_severity_floor(scan_level: str) -> set[str] | None:
    return SEVERITY_FLOOR_MAP.get(scan_level)

def ensure_tools(no_install=False):
    """Auto-install missing tools. Skip if --no-install."""
    if no_install:
        return
    # markdownlint-cli2 (npm)
    _builtin_sp_rules = Path(__file__).parent / "checks" / "skillspector_rules.json"
    if not shutil.which("skillspector") and not _builtin_sp_rules.exists():
        print("  Auto-installing skillspector ...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "skillspector"], check=False)
    # gitleaks (download binary only if builtin rules not available)
    _builtin_rules = Path(__file__).parent / "checks" / "gitleaks_rules.json"
    if not shutil.which("gitleaks") and not _builtin_rules.exists():
        print("  Auto-installing gitleaks ...", flush=True)
        _install_gitleaks()

# ── Discover skills ──

def discover_skills(target: Path):
    """Return list of skill dirs. If target itself has SKILL.md → [target], else find subdirs with SKILL.md."""
    if (target / "SKILL.md").exists():
        return [target]
    skills = sorted([d for d in target.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
    return skills

# ── Run checks ──

def run_cmd(cmd, timeout=120):
    """Run command with shell timeout wrapper to handle stubborn child processes (skill-scanner)."""
    try:
        shell_cmd = f"timeout --signal=KILL {timeout} " + " ".join(shlex.quote(c) for c in cmd)
        r = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True)
        return r.stdout + r.stderr, r.returncode
    except FileNotFoundError:
        return f"ERROR: command not found: {cmd[0]}", 127

def _install_gitleaks():
    """Download and install gitleaks binary."""
    import platform, tempfile, tarfile
    arch = "arm64" if platform.machine() in ("aarch64", "arm64") else "amd64"
    version = "8.25.1"
    filename = f"gitleaks_{version}_linux_{arch}.tar.gz"
    mirrors = [
        f"https://gh-proxy.com/https://github.com/gitleaks/gitleaks/releases/download/v{version}/{filename}",
        f"https://gh.ddlc.top/https://github.com/gitleaks/gitleaks/releases/download/v{version}/{filename}",
    ]
    for url in mirrors:
        try:
            tmp = tempfile.mktemp(suffix=".tar.gz")
            r = subprocess.run(["curl", "-fsSL", "-o", tmp, url, "--connect-timeout", "10", "-m", "120"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                continue
            with tarfile.open(tmp, "r:gz") as tf:
                tf.extractall(path="/usr/local/bin")
            os.unlink(tmp)
            if shutil.which("gitleaks"):
                print("  gitleaks installed successfully", flush=True)
                return
        except Exception:
            continue
    print("  WARNING: gitleaks auto-install failed; install manually from https://github.com/gitleaks/gitleaks/releases", flush=True)

# ── Fix strategies ──

FIX_STRATEGIES = {
    # skillcheck
    "description.quality-score": "Start description with action verb (Generates/Analyzes/Validates); add trigger context like 'Use this skill whenever...'",
    "disclosure.metadata-budget": "Move non-essential frontmatter fields to the body section to reduce token count below 100",
    "disclosure.body-bloat": "Move large tables (>20 rows) to a referenced file under references/ directory",
    "frontmatter.field.unknown": "Add field to skillcheck.toml extension_fields, or remove from frontmatter",
    "compat.unverified": "Document field behavior for codex/cursor or remove unverified fields from frontmatter",
    # markdownlint
    "MD013": "Break long lines; or disable for code blocks/tables in .markdownlint.json: MD013: {code_blocks: false, tables: false}",
    "MD036": "Replace **text** pseudo-headings with ### text real headings",
    "MD031": "Add blank lines before and after fenced code blocks",
    "MD007": "Fix list indentation to match configured indent (default 4 spaces)",
    "MD024": "Add distinguishing suffix to duplicate headings, or enable siblings_only in config",
    # skill-scanner
    "command_injection": "Move dangerous commands (nc, curl|sh, etc.) to standalone scripts under scripts/; reference script path in SKILL.md instead of inline code",
    "reverse_shell": "Remove or relocate reverse shell examples; if needed for documentation, add <!-- skill-scanner:ignore --> annotation",
    "credential_leak": "Replace hardcoded secrets with environment variable references (${VAR}); add to .secrets.baseline if false positive",
    "dangerous_function": "Wrap eval()/exec() calls with input validation; consider safer alternatives like ast.literal_eval()",
    "prompt_injection": "Review and sanitize user-controllable input before embedding in prompts; use structured input templates",
    # skillspector (replaces skill-scanner)
    "P1": "Do not embed user-controllable input in system prompts; use template variables with explicit escaping",
    "P2": "Avoid instructions that override safety guardrails; use allowlists for permitted behaviors",
    "P3": "Separate developer instructions from user data using delimiters; validate input before prompt assembly",
    "P4": "Never include raw file contents in prompts without sanitization; use structured data extraction",
    "P5": "Avoid multi-step reasoning chains that can be hijacked; add integrity checks between steps",
    "E1": "Remove URLs pointing to external servers; use environment variables for API endpoints",
    "E2": "Do not instruct agents to send conversation data externally; restrict network access in tool definitions",
    "E3": "Avoid encoding data in seemingly innocent outputs (base64 in comments, etc.)",
    "E4": "Remove instructions that copy sensitive files to world-readable locations",
    "PE1": "Do not instruct agents to modify system security settings; use least-privilege tool configurations",
    "PE2": "Avoid sudo/root commands in skill scripts; use capability-based permissions",
    "PE3": "Remove instructions that disable security controls (firewalls, audit logs, etc.)",
    "AST1": "Replace exec()/eval() with safer alternatives (ast.literal_eval, subprocess with explicit args)",
    "AST2": "Avoid dynamic module imports with user-controlled names; use importlib with allowlists",
    "AST3": "Do not use __import__ with dynamic strings; map allowed modules explicitly",
    "YR1": "Remove reverse shell patterns; if needed for testing, use isolated sandbox with no network access",
    "YR2": "Remove webshell patterns; move server functionality to separate controlled service",
    "SC1": "Pin dependency versions with hashes; use lock files (requirements.txt with --hash, poetry.lock)",
    "SC4": "Update vulnerable dependency to patched version; check osv.dev for fix versions",
    "LP1": "Reduce MCP tool permissions to minimum required; remove unnecessary file/network access",
    "TP1": "Validate MCP tool metadata against manifest; ensure descriptions match actual behavior",
    # gitleaks
    "generic-api-key": "Replace hardcoded API key/secret with environment variable reference (${VAR} or os.environ.get()); add to .gitleaksignore if false positive",
    "private-key": "Remove hardcoded private key; load from file or secret manager at runtime; add key file to .gitignore",
    "gitleaks": "Replace hardcoded credential with environment variable or secret manager reference; see https://gitleaks.io/docs/secrets for rule-specific remediation",
    # 华为云规范
    "frontmatter": "检查 SKILL.md YAML frontmatter 格式：必需字段(name/description/tags/version)、类型正确、name与目录名一致",
    "section": "按华为云规范补充正文章节：概述、前置条件、核心命令、参数确认、参考文档为必需章节",
    "size": "SKILL.md 建议在500行内，技能目录总大小建议在5MB内，超限时拆分内容到 references/ 子目录",
}

def get_fix_strategy(rule_or_category: str) -> str:
    if rule_or_category in FIX_STRATEGIES:
        return FIX_STRATEGIES[rule_or_category]
    prefix = rule_or_category.split("/")[0].split("_")[0]
    for key in FIX_STRATEGIES:
        if key.lower() == prefix.lower():
            return FIX_STRATEGIES[key]
    return "Review the issue and apply best practices for this category"

# ── Build report ──

def build_report(target: Path, skills: list, results: dict, config):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    L = []
    def a(s=""): L.append(s)

    a("=" * 72)
    a("  Skill Gate Audit Report")
    a(f"  Scan target: {target}")
    a(f"  Skills scanned: {len(skills)}")
    a(f"  Scan level: {config.scan_level}")
    a(f"  Generated: {now}")
    a("=" * 72)
    a()

    # ── Section 1: Scanned Skills ──
    a("── 1. Scanned Skills ──")
    a()
    for s in skills:
        a(f"  ✔ {s.name}")
    a()

    # ── Collect all issues by severity ──
    critical_issues = []
    error_issues = []
    warning_issues = []

    for source, result in results.items():
        for issue in result.issues:
            entry = {
                "skill": "", "source": source,
                "rule": issue.rule, "severity": issue.severity.value,
                "message": issue.message, "line": issue.line,
                "file": issue.file, "snippet": issue.snippet,
                "category": issue.category,
                "rule_prefix": issue.rule.split("/")[0].split("_")[0] if issue.rule else "",
            }
            if issue.severity == Severity.CRITICAL:
                critical_issues.append(entry)
            elif issue.severity == Severity.ERROR:
                error_issues.append(entry)
            elif issue.severity == Severity.WARNING:
                warning_issues.append(entry)

    # ── Section 2: Issue Summary ──
    a("── 2. Issue Summary ──")
    a()
    if critical_issues:
        cats = {}
        for i in critical_issues:
            c = i.get("category", i["rule"])
            cats[c] = cats.get(c, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(cats.items()))
        src = set(i["source"] for i in critical_issues)
        a(f"  CRITICAL  {len(critical_issues):>3}  {detail} ({', '.join(src)})")
    if error_issues:
        rules = {}
        for i in error_issues:
            r = i.get("rule_prefix", i["rule"])
            rules[r] = rules.get(r, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(rules.items()))
        src = set(i["source"] for i in error_issues)
        a(f"  ERROR    {len(error_issues):>3}  {detail} ({', '.join(src)})")
    if warning_issues:
        rules = {}
        for i in warning_issues:
            r = i["rule"]
            rules[r] = rules.get(r, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(rules.items()))
        src = set(i["source"] for i in warning_issues)
        a(f"  WARNING  {len(warning_issues):>3}  {detail} ({', '.join(src)})")
    if not critical_issues and not error_issues and not warning_issues:
        a("  (no issues found)")
    a()

    # ── Section 3: Issue Details ──
    a("── 3. Issue Details ──")
    a()

    def detail_block(issues, label):
        if not issues:
            return
        for i in issues:
            a(f"  [{label}] {i['skill']} — {i.get('category', i['rule'])}")
            location_parts = []
            if i.get("file"):
                location_parts.append(i["file"])
            if i.get("line"):
                location_parts.append(f"L{i['line']}")
            if location_parts:
                a(f"    {' '.join(location_parts)}  {i['rule']}")
            else:
                a(f"    {i['rule']}")
            if i.get("snippet"):
                a(f"    Snippet: {i['snippet'][:120]}")
            if i.get("message"):
                a(f"    {i['message'][:150]}")
            a()

    detail_block(critical_issues, "CRITICAL")
    detail_block(error_issues, "ERROR")
    detail_block(warning_issues, "WARNING")

    # ── Section 4: Fix Strategies ──
    a("── 4. Fix Strategies ──")
    a()

    seen_rules = set()
    all_issues = critical_issues + error_issues + warning_issues
    for i in all_issues:
        rule_key = i.get("category") or i.get("rule_prefix") or i["rule"]
        if rule_key in seen_rules:
            continue
        seen_rules.add(rule_key)
        sev = i["severity"].upper() if i["severity"] not in ("error",) else "ERROR"
        strategy = get_fix_strategy(rule_key)
        a(f"  [{sev}] {rule_key}")
        a(f"    Strategy: {strategy}")
        a()

    if not seen_rules:
        a("  (no issues to fix)")
        a()

    # ── Verdict ──
    a("=" * 72)
    checks_list = []
    for name, result in results.items():
        checks_list.append((name, result.passed))
    pass_count = sum(1 for _, v in checks_list if v)
    total = len(checks_list)
    if pass_count == total:
        a(f"  Gate Verdict: PASS  |  {'  '.join(f'{n} OK' for n, _ in checks_list)}")
    else:
        parts = [f"{n} OK" if v else f"{n} FAIL" for n, v in checks_list]
        a(f"  Gate Verdict: FAIL  |  {'  '.join(parts)}")

    # SkillSpector risk metadata
    if "skillspector" in results and results["skillspector"].raw_output:
        a(f"  skillspector: {results['skillspector'].raw_output}")

    a("=" * 72)

    return "\n".join(L)

# ── Main ──

def main():
    args = parse_args()
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"ERROR: target not found: {target}", file=sys.stderr)
        sys.exit(1)

    try:
        enabled = resolve_enabled_checks(args.checks, args.skip_checks)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    config = AuditConfig(
        scan_level=args.scan_level,
        enabled_checks=enabled,
        check_bins={
            k: v for k, v in {
                "skillspector": args.skillspector,
                "gitleaks": args.gitleaks,
            }.items() if v
        },
        no_install=args.no_install,
        node_bin=args.node_bin,
    )

    ensure_tools(no_install=args.no_install)

    skills = discover_skills(target)
    if not skills:
        print(f"ERROR: no skills found under: {target}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else target.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {len(skills)} skill(s) under {target} (level: {config.scan_level}) ...")

    checks = create_checks(config)
    results: dict[str, CheckResult] = {}

    for i, check in enumerate(checks, 1):
        label = f"[{i}/{len(checks)}] {check.name}"
        if not check.is_available():
            print(f"  {label} ... SKIP (not available)")
            results[check.name] = CheckResult(source=check.name, passed=True,
                                              raw_output="SKIPPED (not available)")
            continue
        print(f"  {label} ...", end=" ", flush=True)
        result = check.run_batch(target, skills)
        result.issues = [i for i in result.issues if i.severity != Severity.INFO]
        result.passed = not any(i.severity in (Severity.CRITICAL, Severity.ERROR) for i in result.issues)
        results[check.name] = result
        issue_count = len(result.issues)
        print(f"{'OK' if result.passed else f'{issue_count} issues'}")

    severity_floor = _get_severity_floor(config.scan_level)
    if severity_floor is not None:
        for name, result in results.items():
            if name != "skillspector":
                continue
            before = len(result.issues)
            result.issues = [i for i in result.issues if i.severity.value in severity_floor]
            result.passed = len(result.issues) == 0
            if before != len(result.issues):
                print(f"    (filtered to {len(result.issues)} issues by severity floor: {severity_floor})")

    report = build_report(target, skills, results, config)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    report_path = output_dir / f"skill-gate-report-{ts}.txt"
    report_path.write_text(report, encoding="utf-8")

    print(f"\nReport saved: {report_path}")
    return report_path

if __name__ == "__main__":
    main()
