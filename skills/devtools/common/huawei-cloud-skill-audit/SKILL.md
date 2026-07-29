---
name: huawei-cloud-skill-audit
description: |
  Audit Huawei Cloud skills for quality, security, and compliance using a five-check pipeline:
  skillcheck (agentskills.io spec), markdownlint-cli2 (style), skillspector (AI security),
  hwcloud-spec (Huawei Cloud SKILL.md spec), and gitleaks (credential leak).
  Generates structured reports with issue details and fix strategies.
  Triggers include: "审计技能","技能审计","检查技能质量","扫描技能问题","技能安全审计",
  "audit skill","check skill quality","scan skills for issues","skill audit",
  "华为云技能审计","技能合规检查","skill gate","质量门禁","技能检查",
  "audit huawei cloud skill","verify skill compliance","技能质量检查","跑审计","安全扫描".
tags: [huawei-cloud, audit, security, quality, compliance, devops]
---

# Huawei Cloud Skill Audit

> Two-check security pipeline for auditing Huawei Cloud skills — security gate.

---

## Overview

Scan a single Huawei Cloud skill directory or a folder of skills, run two security gates, and generate a structured report with issue details and fix strategies.

**Two checks:**

| # | Tool | Check Content | Implementation |
|---|------|--------------|---------------|
| 1 | **skillspector** | AI skill security scanner: 47 rules / 439 patterns across 17 categories (prompt injection, data exfiltration, privilege escalation, supply chain, behavioral AST, taint tracking, MCP analysis, YARA) | **Built-in** (pure Python, 47 rules + AST analysis) |
| 2 | **gitleaks** | Credential leak scan: 222 rules detecting hardcoded API keys, passwords, private keys, tokens, and 800+ credential formats | **Built-in** (pure Python, 222 rules + Shannon entropy) |

---

## Prerequisites

1. **Python 3.10+** — Required by skillcheck; Python 3.12+ for external skillspector binary (builtin has no Python version restriction)
2. **Node.js + npx** — Required by markdownlint-cli2
3. **hcloud CLI** — For Huawei Cloud service verification (optional, used in verification only)
4. **Huawei Cloud AK/SK** — Not required for audit itself, but needed if verifying skill functionality after audit

skillspector and gitleaks are **built-in** (pure Python) — no external binary or pip install needed. External binaries are used as fallback if available on PATH.

Tools are **auto-installed** on first run (only skillcheck and markdownlint-cli2). If you prefer manual install:

```bash
pip install skillcheck
npm install -g markdownlint-cli2
```

To skip auto-install, use `--no-install` flag.

---

## Workflow

```
Input (skill path or folder)
    │
    ├── Discover Skills ──── Find SKILL.md in target or subdirectories
    │
    ├── Run Two Checks ────
    │   1. skillspector → AI security scan (47 rules, 439 patterns)
    │   2. gitleaks → Credential leak detection
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
| `critical` | CRITICAL severity rules only (P5 harmful content) | Fast | Strictest gate, default |
| `high` | CRITICAL + ERROR severity rules | Fast | Block high-risk issues |
| `quick` | Pattern matching only (all static regex rules) | Fast | Quick pre-commit check |
| `standard` | All static analyzers (quick + AST + taint tracking) | Medium | CI/CD gate |
| `deep` | Standard + MCP analysis (least privilege, tool poisoning, rug pull) | Slower | Pre-release full audit |

**Severity filtering applies only to SkillSpector.** gitleaks, hwcloud-spec, skillcheck, and markdownlint always report all findings regardless of scan level.

---

## KooCLI Command Format Standard

This skill does not directly invoke `hcloud` CLI commands. It audits skill directories locally. However, when verifying a skill's functionality after audit, the standard KooCLI format applies:

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

---

## Core Commands

### Scan a single skill

```bash
python3 scripts/skill_audit.py --target /path/to/my-skill
```

### Scan a folder of skills

```bash
python3 scripts/skill_audit.py --target /path/to/skills-folder
```

### Scan with specific level

```bash
python3 scripts/skill_audit.py --target /path/to/skills --scan-level quick
```

### Selective check execution

```bash
python3 scripts/skill_audit.py --target /path/to/skills --checks skillspector
python3 scripts/skill_audit.py --target /path/to/skills --skip-checks markdownlint
```

### Run with custom tool paths

```bash
python3 scripts/skill_audit.py \
  --target /path/to/skill-or-folder \
  --scan-level standard \
  --skillspector /path/to/skillspector \
  --gitleaks /path/to/gitleaks \
  --node-bin /opt/nvm/versions/node/v18.20.8/bin
```

Available `--scan-level` values: `critical` (default), `high`, `quick`, `standard`, `deep`.
Available `--checks`: `skillspector`, `gitleaks`.
Use `--skip-checks` to exclude specific checks.

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--target` | Yes | Single skill dir or parent folder of skills | `/home/user/.hermes/skills/huawei-cloud-ecs-manage` |
| `--output-dir` | No | Report output directory (default: parent of target) | `--output-dir ./reports` |
| `--scan-level` | No | Scan depth: critical/high/quick/standard/deep (default: critical) | `--scan-level deep` |
| `--checks` | No | Comma-separated checks to run (default: all) | `--checks skillspector` |
| `--markdownlint` | No | markdownlint-cli2 binary path override | `--markdownlint /usr/local/bin/markdownlint-cli2` |
| `--skillspector` | No | SkillSpector binary path override | `--skillspector /usr/local/bin/skillspector` |
| `--gitleaks` | No | gitleaks binary path override | `--gitleaks /usr/local/bin/gitleaks` |
| `--no-install` | No | Skip auto-install of tools | `--no-install` |

---

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

### hwcloud-spec (Huawei Cloud SKILL.md Spec)

| Rule | Fix |
|------|-----|
| frontmatter.missing.{field} | Add required field: name (match dir name), description (include summary + triggers), tags (<=5); recommended: version (semver like 1.0.0) |
| frontmatter.name-mismatch | name field value must exactly match the skill directory name |
| frontmatter.tags-too-many | Reduce tags to 5 or fewer |
| frontmatter.version-format | version must follow semver format (e.g. 2.0.0) |
| frontmatter.description-too-short | description should include: feature summary, tech basis, use cases, trigger words |
| section.missing-required | Add required sections: Overview, Prerequisites, Core Commands, Parameter Confirmation, Reference Documents |
| section.missing-recommended | Add recommended sections: Output Format, Verification Method, Best Practices, Notes |
| size.skill-md-lines | SKILL.md exceeds 500 lines — split content into references/ subdirectory |
| size.dir-too-large | Skill directory exceeds 5MB — split large files into references/ or scripts/ |

### markdownlint-cli2

| Rule | Fix |
|------|-----|
| MD013 line-length | Break long lines; or disable for code blocks in .markdownlint.json |
| MD036 no-emphasis-as-heading | Replace **text** pseudo-headings with ### text real headings |
| MD031 blanks-around-fences | Add blank lines before/after fenced code blocks |
| MD007 ul-indent | Fix list indentation to match configured indent (default 4) |
| MD024 no-duplicate-heading | Add distinguishing suffix or enable siblings_only |

### skillspector

| Rule | Fix |
|------|-----|
| P1-P5 (Prompt Injection) | Do not embed user-controllable input in system prompts; use template variables with explicit escaping |
| E1-E4 (Data Exfiltration) | Remove external URLs; use env vars for API endpoints; restrict network access in tool definitions |
| PE1-PE3 (Privilege Escalation) | Avoid sudo/root commands; use capability-based permissions; do not disable security controls |
| AST1-AST3 (Behavioral AST) | Replace exec()/eval() with safer alternatives; use importlib with allowlists |
| YR1-YR4 (YARA) | Remove reverse shell/webshell patterns; move server functionality to separate controlled service |
| SC1-SC6 (Supply Chain) | Pin dependency versions with hashes; update vulnerable dependencies |
| LP1-LP4 (MCP Least Privilege) | Reduce MCP tool permissions to minimum required |
| TP1-TP4 (MCP Tool Poisoning) | Validate MCP tool metadata against manifest |

### gitleaks

| Rule | Fix |
|------|-----|
| generic-api-key | Replace hardcoded API key/secret with `os.environ.get("VAR")` or `${VAR}`; add to `.gitleaksignore` if false positive |
| private-key | Remove hardcoded private key; load from file or secret manager at runtime; add key file to `.gitignore` |
| (other rules) | Replace hardcoded credential with environment variable or secret manager reference; see https://gitleaks.io/docs/secrets |

---

## Remediation Workflow (audit -> fix -> verify)

After running the audit and getting a FAIL, follow this sequence:

1. **Run `markdownlint-cli2 --fix` FIRST** — auto-fixes MD022/MD031/MD032/MD047/MD012/MD009/MD010 and many more.
   ```bash
   markdownlint-cli2 "skills/my-skill/**/*.md" --config "skills/my-skill/.markdownlint.json" --fix
   ```

   2. **Fix hwcloud-spec missing sections** — Add required sections by hand (require domain knowledge).

   3. **Fix MD036 (emphasis-as-heading)** — Replace `*text*` or `**text**` pseudo-heading with `### heading` or plain text.

   4. **Fix MD040 (fenced-code-language)** — Replace bare ` ``` ` with ` ```text ` or the appropriate language.

   5. **Run `markdownlint-cli2 --fix` AGAIN** — Catch new issues from manual edits.

   6. **Re-run the full audit** to verify PASS.

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
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm install -g markdownlint-cli2
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

### skillcheck.toml

```toml
[frontmatter]
extension_fields = [
    "license",
    "platforms",
    "metadata",
    "prerequisites",
]
```

### .markdownlint.json

```json
{
  "default": true,
  "MD003": { "style": "atx" },
  "MD004": { "style": "dash" },
  "MD013": { "line_length": 200, "code_blocks": false, "tables": false },
  "MD024": { "siblings_only": true },
  "MD033": false,
  "MD034": false,
  "MD040": false,
  "MD041": false,
  "MD046": false,
  "MD047": false,
  "MD058": false
}
```

---

## Security Scanning

### Why skillspector static-only mode has limitations

`skillspector` runs with `--no-llm` mode (static analysis only). Gaps:

| Analyzer | What it detects | What it MISSES in --no-llm mode |
|----------|----------------|--------------------------------|
| Pattern matching (P1-P5, E1-E4, PE1-PE3) | Prompt injection, data exfiltration, privilege escalation patterns | LLM-generated obfuscated variants |
| AST analysis (AST1-AST3) | exec()/eval() calls, dynamic imports | Runtime-evaluated strings |
| YARA rules (YR1-YR4) | Reverse shell, webshell patterns | Encoded/obfuscated payloads |
| Supply chain (SC1-SC6) | Vulnerable/pinned dependency issues | Transitive dependency exploits |

### Complementary tools

| Tool | Detects | Install |
|------|---------|---------|
| skillspector (built-in, --no-llm) | Prompt injection, reverse shell, command injection, data exfiltration, privilege escalation, supply chain | Auto-installed |
| gitleaks (built-in) | 800+ credential types: API keys, passwords, private keys, tokens | Auto-installed |
| gitcode-security-scanner | Generic keyword credentials, Chinese keywords, SQL injection, debug leakage | From DTSE-SKILL repo |

**Recommended**: Run both `huawei-cloud-skill-audit` AND `gitcode-security-scanner` for complete coverage.

---

## Output Format

Report is a plain text file with four sections (Scanned Skills, Issue Summary, Issue Details, Fix Strategies) followed by a Gate Verdict (PASS/FAIL).

---

## Verification Method

### Run audit

```bash
python3 scripts/skill_audit.py --target /path/to/skill
```

### Verify fix

```bash
# Auto-fix markdownlint issues
markdownlint-cli2 "/path/to/skill/**/*.md" --config "/path/to/skill/.markdownlint.json" --fix

# Re-run audit
python3 scripts/skill_audit.py --target /path/to/skill
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

---

## Best Practices

- Run audit before accepting any Huawei Cloud skill contribution
- Fix markdownlint issues with `--fix` first, then fix non-auto-fixable items manually
- Always re-run full audit after fixing to verify PASS
- For large repos, scan individual skills one at a time to avoid huge reports
- Run both `huawei-cloud-skill-audit` and `gitcode-security-scanner` for complete security coverage

---

## Notes

- Five-check pipeline runs sequentially; each check is independent
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
| markdownlint-cli2 not found | Auto-install via npm |
| Python version < 3.12 | External skillspector binary not available; builtin still works |
| Node/npx not on PATH | Pass --node-bin to specify Node binary directory |
| Large repo produces huge report | Scan individual skills; use head/tail to read summary |
| gitleaks false positive | Add to .gitleaksignore file |
| skillspector exit code 1 | Risk score > 50; treated as finding source, not hard failure |

---

## Design Principles

- **Two-Check Pipeline** — Each check is independent and contributes to the overall gate verdict
- **Auto-Install** — Missing tools are installed automatically on first run
- **Chain Verification** — All five checks must pass for gate verdict PASS
- **Agent-proof** — Write operations require user confirmation; automatic gate bypassing is not allowed
- **Data-Driven** — Report is structured text with clear severity levels and fix strategies
- **Batch Repeatable** — Same skill can be audited repeatedly; --fresh resets
- **Credential Security** — No hardcoded AK/SK; read from environment variables
- **Least Privilege** — IAM policies follow minimum required permissions
