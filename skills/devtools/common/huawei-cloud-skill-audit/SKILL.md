---
name: huawei-cloud-skill-audit
description: |
  Audit Huawei Cloud skills for quality, security, and compliance using a three-check pipeline:
  skillspector (AI security) and gitleaks (credential leak).
  Generates structured reports with issue details and fix strategies.
  Triggers include: "审计技能","技能审计","检查技能质量","扫描技能问题","技能安全审计",
  "audit skill","check skill quality","scan skills for issues","skill audit",
  "华为云技能审计","技能合规检查","skill gate","质量门禁","技能检查",
  "audit huawei cloud skill","verify skill compliance","技能质量检查","跑审计","安全扫描".
tags: [huawei-cloud, audit, security, quality, compliance, devops]
---

# Huawei Cloud Skill Audit

> Three-check security pipeline for auditing Huawei Cloud skills — security gate.

---

<!-- cli-install-version: 3.8.0 -->
## Step 0: Install skill-quality-cli (idempotent, skip if already installed)

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-skill-audit -- ` — bare `hcloud` calls are strictly forbidden.**

> **⚠️ 强制要求：执行本 skill 的任何 hcloud 命令必须用 `skill-quality-cli run --skill-name huawei-cloud-skill-audit -- ` 包裹，禁止裸调 hcloud。**

bash scripts/ensure_cli.sh
```
> The script detects whether `skill-quality-cli` is available; if not, it downloads the tar.gz package (wrapper + ELF + Python fallback, low-GLIBC compatible) and installs it to `~/.local/bin/`. Silently skipped when offline — never blocks the business flow.
## Overview

Scan a single Huawei Cloud skill directory or a folder of skills, run three security gates, and generate a structured report with issue details and fix strategies.

**Three checks:**

| # | Tool | Check Content | Implementation |
|---|------|--------------|---------------|
| 1 | **skillspector** | AI skill security scanner: 51 rules / 609 patterns across 17 categories (prompt injection, data exfiltration, privilege escalation, supply chain, behavioral AST, taint tracking, MCP analysis, YARA) | **Built-in** (pure Python, 51 rules + AST analysis) |
| 2 | **gitleaks** | Credential leak scan: 42 rules detecting hardcoded API keys, passwords, private keys, tokens | **Built-in** (pure Python, 42 rules + Shannon entropy) |
| 3 | **runtime_security** | CWE high-risk runtime patterns: 36 rules (command injection, deserialization, credential theft, sandbox escape, persistence, destructive ops, mining) + 3 skill-quality rules (Q001-Q003) | **Built-in** (pure Python, level-independent, all rules always run) |

---

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

1. **Python 3.10+** — for the built-in skillspector and gitleaks checks
2. **Node.js + npx** — Optional; only needed for manual `markdownlint-cli2 --fix` during remediation
3. **hcloud CLI** — For Huawei Cloud service verification (optional, used in verification only)
4. **Huawei Cloud AK/SK** — Not required for audit itself, but needed if verifying skill functionality after audit

skillspector and gitleaks are **built-in** (pure Python) — no external binary or pip install needed. External binaries are used as fallback if available on PATH.

To skip fallback auto-install of external binaries, use `--no-install` flag.

---
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_DISABLE=1`
## Workflow

```
Input (skill path or folder)
    │
    ├── Discover Skills ──── Find SKILL.md in target or subdirectories
    │
    ├── Run Three Checks ────
    │   1. skillspector → AI security scan (51 rules, 609 patterns)
    │   2. gitleaks → Credential leak detection
    │   3. runtime_security → CWE high-risk runtime patterns (36 + 3 rules)
    │
    ├── Build Report ────
    │   Section 1: Scanned Skills
    │   Section 2: Issue Summary (by severity)
    │   Section 3: Issue Details (per-issue)
    │   Section 4: Fix Strategies (per rule/category)
    │
    └── Gate Verdict ──── PASS or FAIL
```

---

## Scan Levels

| Level | Analyzers | Speed | Use Case |
|-------|-----------|-------|----------|
| `critical` | CRITICAL severity rules only (P5 harmful content) | Fast | Strictest gate |
| `high` | CRITICAL + ERROR severity rules + AST (exec/eval/os.system/反序列化) | Fast | Block high-risk issues |
| `quick` | Pattern matching only (all static regex rules) | Fast | Quick pre-commit check |
| `standard` | All static analyzers (high 基础上放开 WARNING/INFO 级 AST + taint tracking) | Medium | CI/CD gate |
| `deep` | Standard + MCP analysis (least privilege, tool poisoning, rug pull) | Slower | Pre-release full audit |

**Severity filtering applies only to SkillSpector** (rule selection per scan level). gitleaks bundles only critical/high rules, so all of them run at every scan level. runtime_security is level-independent: all 39 rules (36 CWE + Q001-Q003) always run, and its CRITICAL findings always block the gate.

**AST 分析在 high/standard/deep 均执行**(high 为默认档, 必须带 AST, 否则 eval/exec/pickle.loads 等执行类检测可被直接绕过)。high 档楼层过滤保留 critical/high 级发现, 因此默认档阻断: AST1/2/5/9/10(exec/eval/os.system/getattr 反射/反序列化全部 ERROR 级); WARNING 级(AST3/4/6/7: compile/subprocess/动态 import 等)仅在 standard/deep 可见。.py 解析失败不再静默——产出 ERROR 级 AST-SYNTAX 发现并阻断 gate(fail-closed, 防恶意写坏代码规避 AST)。

---

## KooCLI Command Format Standard

This skill audits skill directories locally and does not directly invoke `hcloud` CLI commands.
When verifying a skill's functionality after audit, the standard KooCLI format applies — the line below is an **illustrative template, not a runnable command**:

```text
bash scripts/hcloud-run.sh <Service> <Operation> --cli-region=<region> [--key=value ...]   # 强制入口：一切 hcloud 经 hcloud-run.sh 包装执行
```

---

## Core Commands

> The examples below use real, always-existing directories (`.` = current directory, `..` = parent directory) so every command is executable as-is: run from inside a skill directory to audit that single skill, or from a parent folder to audit all skills under it. Any existing skill directory path works the same way.

### Scan a single skill

```bash
# Run from inside the skill directory
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target .
```

### Scan a folder of skills

```bash
# Run from the parent folder that contains the skills
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target ..
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target ..
```

### Scan with specific level

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .. --scan-level quick
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target .. --scan-level quick
```

### Selective check execution

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .. --checks skillspector
python3 scripts/skill_audit.py --target .. --checks skillspector
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .. --skip-checks gitleaks
python3 scripts/skill_audit.py --target .. --skip-checks gitleaks
```

### Run with custom tool paths

Custom binary locations can be overridden with `--skillspector`, `--gitleaks` and `--node-bin` (see Parameter Confirmation; default auto-install location is `~/.local/bin/`):

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .. --scan-level standard
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target .. --scan-level standard
```

Available `--scan-level` values: `high` (default), `critical`, `quick`, `standard`, `deep`.
Available `--checks`: `skillspector`, `gitleaks`, `runtime_security`.
Use `--skip-checks` to exclude specific checks.

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--target` | Yes | Single skill dir or parent folder of skills | `/path/to/skill-dir` |
| `--output-dir` | No | Report output directory (default: parent of target) | `--output-dir ./reports` |
| `--scan-level` | No | Scan depth: high/critical/quick/standard/deep (default: high) | `--scan-level deep` |
| `--checks` | No | Comma-separated checks to run (default: all); valid values are only `skillspector`, `gitleaks`, `runtime_security`. Mutually exclusive with `--skip-checks` | `--checks skillspector` |
| `--skillspector` | No | SkillSpector binary path override | `--skillspector ~/.local/bin/skillspector` |
| `--gitleaks` | No | gitleaks binary path override (auto-installs to ~/.local/bin when missing) | `--gitleaks ~/.local/bin/gitleaks` |
| `--skip-checks` | No | Comma-separated checks to skip; mutually exclusive with `--checks` | `--skip-checks gitleaks` |
| `--no-install` | No | Skip auto-install of tools | `--no-install` |

## Report Structure

Report is saved as `skill-gate-report-<timestamp>.txt` in the parent directory of the scanned path.

| Input | Report saved to |
|-------|----------------|
| `/repo/skills/huawei-cloud-ecs-manage` | `/repo/skills/skill-gate-report-<timestamp>.txt` |
| `/repo/skills` | `/repo/skill-gate-report-<timestamp>.txt` |

Four sections:

1. **Scanned Skills** — list of all skills found
2. **Issue Summary** — count by severity (CRITICAL/ERROR/WARNING) with rule breakdown (INFO excluded)
3. **Issue Details** — per-issue: skill name, rule, line number, snippet, message
4. **Fix Strategies** — actionable remediation for each unique rule/category

---

## Fix Strategies Reference

### skillspector

| Rule | Fix |
|------|-----|
| P1-P8 (Prompt Injection / System Prompt Leakage) | Do not embed user-controllable input in system prompts; use template variables with explicit escaping |
| E1-E5 (Data Exfiltration) | Remove external URLs; use env vars for API endpoints; restrict network access in tool definitions |
| PE1-PE5 (Privilege Escalation) | Avoid sudo/root commands; use capability-based permissions; do not disable security controls |
| AST (Behavioral AST: AST1-AST7/9/10) | Replace exec()/eval() with safer alternatives; use importlib with allowlists |
| YR1-YR4 (YARA) | Remove reverse shell/webshell patterns; move server functionality to separate controlled service |
| SC1/SC2/SC3/SC7 (Supply Chain) | Pin dependency versions with hashes; update vulnerable dependencies |
| EA1-EA4 (Excessive Agency) | Scope tool permissions to the minimum required for the task |
| MP1-MP3, OH1-OH3 (Memory Poisoning / Output Handling) | Validate memory writes and tool output before use |
| RA1-RA2, AS1-AS3 (Rogue Agent / Agent Snooping) | Restrict agent delegation and session data access |
| SSRF1-SSRF3 (Server-Side Request Forgery) | Validate/allowlist external endpoints before requests |
| TM1-TM4 (Tool Misuse) | Validate tool parameters; never concatenate untrusted input into shell commands |

### gitleaks

| Rule | Fix |
|------|-----|
| private-key | Remove hardcoded private key; load from file or secret manager at runtime; add key file to `.gitignore` |
| (other rules) | Replace hardcoded credential with environment variable or secret manager reference; see https://gitleaks.io/docs/secrets |

---

## Remediation Workflow (audit -> fix -> verify)

After running the audit and getting a FAIL, follow this sequence:

1. **Fix issues by hand** — Apply the fixes from the report's Fix Strategies section, or the skillspector/gitleaks rule tables above.
2. **Re-run the full audit** to verify PASS.

> Markdown style and SKILL.md spec issues are not audited by this skill; use external tools like `markdownlint-cli2 --fix` only if you need to fix markdown style separately.

---

## CI/CD Integration

```yaml
jobs:
  skill-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run audit
        run: python3 scripts/skill_audit.py --target . --output-dir .
      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: skill-gate-report
          path: skill-gate-report-*.txt
```

---

## Configuration Files

The built-in checks use their bundled rule sets — no external config required:

- `scripts/checks/skillspector_rules.json` — skillspector rules (51 rules / 609 patterns)
- `scripts/checks/gitleaks_rules.json` — gitleaks rules (42 rules)

`.markdownlint.json` and `skillcheck.toml` shipped with the skill directory are **not** consumed by this audit; they are only for external markdownlint/skillcheck tooling.

---

## Security Scanning

### Why skillspector static-only mode has limitations

`skillspector` runs with `--no-llm` mode (static analysis only). Gaps:

| Analyzer | What it detects | What it MISSES in --no-llm mode |
|----------|----------------|--------------------------------|
| Pattern matching (P1-P8, E1-E5, PE1-PE5, EA1-EA4, MP1-MP3, OH1-OH3, RA1-RA2, AS1-AS3, SSRF1-SSRF3, TM1-TM4) | Prompt injection, data exfiltration, privilege escalation, agency/poisoning patterns | LLM-generated obfuscated variants |
| AST analysis (AST1-AST7/9/10) | exec()/eval() calls, dynamic imports, reflective getattr, unsafe deserialization | Runtime-evaluated strings |
| YARA rules (YR1-YR4) | Reverse shell, webshell patterns | Encoded/obfuscated payloads |
| Supply chain (SC1/SC2/SC3/SC7) | Vulnerable/pinned dependency issues | Transitive dependency exploits |

### Complementary tools

| Tool | Detects | Install |
|------|---------|---------|
| skillspector (built-in, --no-llm) | Prompt injection, reverse shell, command injection, data exfiltration, privilege escalation, supply chain | Auto-installed |
| gitleaks (built-in) | 42 rules: API keys, passwords, private keys, tokens | Auto-installed |
| gitcode-security-scanner | Generic keyword credentials, Chinese keywords, SQL injection, debug leakage | From DTSE-SKILL repo |

**Recommended**: Run both `huawei-cloud-skill-audit` AND `gitcode-security-scanner` for complete coverage.

---

## Output Format

Report is a plain text file with four sections (Scanned Skills, Issue Summary, Issue Details, Fix Strategies) followed by a Gate Verdict (PASS/FAIL).

---

## Verification Method

### Run audit

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target .
```

### Verify fix

```bash
# Fix issues from the report's Fix Strategies section, then re-run audit
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 scripts/skill_audit.py --target .
# 等效直接执行（不经 CLI 包装，无质量上报）
python3 scripts/skill_audit.py --target .
```

### Check gate verdict

```bash
# Gate Verdict: PASS = all checks passed
# Gate Verdict: FAIL = one or more checks have issues
```

---

## Reference Documents

- `references/iam-policies.md` — IAM permissions required for skill audit
- `references/verification-method.md` — Detailed verification procedures
- `references/acceptance-criteria.md` — Acceptance criteria for audit PASS
- `references/security-audit-guide.md` — Security audit guide and fix strategies
- `references/gitcode-security-scanner.md` — Complementary scanner usage guide
- `scripts/ensure_cli.sh` — Idempotent skill-quality-cli installer (auto-installs if absent)

---

## Best Practices

- Run audit before accepting any Huawei Cloud skill contribution
- Fix issues per the report's Fix Strategies, then always re-run full audit to verify PASS
- For large repos, scan individual skills one at a time to avoid huge reports
- Run both `huawei-cloud-skill-audit` and `gitcode-security-scanner` for complete security coverage

---

## Notes

- This skill only generates audit reports and fix strategies; it **never modifies any skill file automatically**. Fixes are applied manually by the user per the report's Fix Strategies or the Remediation Workflow; re-run the audit to verify after fixing.
- Three-check pipeline runs sequentially; each check is independent
- API endpoints are strictly prohibited from being inferred
- Credentials (AK/SK) are read from environment variables; hardcoding is prohibited
- **If AK/SK is missing for post-audit verification, prompt the user; do not skip**
- Resources created during testing must be tracked; output manual cleanup instructions if any remain
- INFO-level issues are excluded from the report; only CRITICAL/ERROR/WARNING appear
- gitleaks `--no-git` mode scans current file contents only, not git history
- gitleaks does not detect Chinese keyword credentials; use gitcode-security-scanner for those

---

## Edge Cases

| Scenario | Handling |
|----------|---------|
| Skill directory does not exist | Report error and terminate |
| Target has no SKILL.md and no subdirs with SKILL.md | Report error: no skills found |
| Built-in rules file missing | Auto-download fallback binary (skillspector/gitleaks) |
| Python version < 3.12 | External skillspector binary not available; builtin still works |
| Large repo produces huge report | Scan individual skills; use head/tail to read summary |
| gitleaks false positive | Add to .gitleaksignore file |
| skillspector exit code 1 | Risk score > 50; treated as finding source, not hard failure |

---

## Design Principles

- **Two-Check Pipeline** — Each check is independent and contributes to the overall gate verdict
- **Auto-Install** — Missing tools are installed automatically on first run
- **Chain Verification** — All enabled checks must pass for gate verdict PASS
- **Agent-proof** — Write operations require user confirmation; automatic gate bypassing is not allowed
- **Data-Driven** — Report is structured text with clear severity levels and fix strategies
- **Batch Repeatable** — Same skill can be audited repeatedly; each run writes a fresh timestamped report
- **Credential Security** — No hardcoded AK/SK; read from environment variables
- **Least Privilege** — IAM policies follow minimum required permissions


