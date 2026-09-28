---
name: huawei-cloud-skill-audit
description: |
  Audit Huawei Cloud skills for quality, security, and compliance using a three-check pipeline:
  skillspector (AI security), gitleaks (credential leak), and runtime_security (CWE 高危运行模式).
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

> 先设置 `AUDIT_DIR` 为本 skill 安装目录的绝对路径(`export AUDIT_DIR=/path/to/huawei-cloud-skill-audit`,
> 示例: `$HOME/.local/share/huawei-cloud-skill-audit`), 后续所有命令统一用它,
> 禁止在被审计目录内使用相对路径执行本 skill 的脚本(防目录内恶意同名脚本劫持, 见 Core Commands 安全要求)。

```bash
export AUDIT_DIR=/path/to/huawei-cloud-skill-audit   # 替换为实际安装目录
bash "$AUDIT_DIR/scripts/ensure_cli.sh"
```
> **⚠️ 强制要求**: 本 skill 的任何 `hcloud` 命令必须用 `skill-quality-cli run --skill-name huawei-cloud-skill-audit -- ` 包裹, 禁止裸调 hcloud。(Mandatory: bare `hcloud` calls are strictly forbidden.)
>
> 安装行为说明:
> - 已装且可用 → 静默跳过; 未装 → 从华为云 OBS(HTTPS) 下载官方包(wrapper + ELF + Python fallback, low-GLIBC 兼容)安装到 `~/.local/bin/`。
> - 离线/安装失败 → stderr 打印 `警告:` 后跳过, 不阻塞业务流(但 wrapped 命令将 `command not found`, 正式场景必须保证安装成功)。
> - 调试/离线场景可用裸命令 `python3 "$AUDIT_DIR/scripts/skill_audit.py" ...`(见 Core Commands 安全要求与统一说明)。
## Overview

Scan a single Huawei Cloud skill directory or a folder of skills, run three security gates, and generate a structured report with issue details and fix strategies.

**Three checks:**

| # | Tool | Check Content | Implementation |
|---|------|--------------|---------------|
| 1 | **skillspector** | AI skill security scanner: 52 rules / 609 patterns across 18 categories (prompt injection, data exfiltration, privilege escalation, supply chain, behavioral AST, taint tracking, MCP analysis, YARA) | **Built-in** (pure Python, 52 rules + AST analysis) |
| 2 | **gitleaks** | Credential leak scan: 43 rules detecting hardcoded API keys, passwords, private keys, tokens | **Built-in** (pure Python, 43 rules + Shannon entropy) |
| 3 | **runtime_security** | CWE high-risk runtime patterns: 36 rules (command injection, deserialization, credential theft, sandbox escape, persistence, destructive ops, mining) + 3 skill-quality rules (Q001-Q003) | **Built-in** (pure Python, level-independent, all rules always run) |

> 规则数(52/609、43、36+3)以 `scripts/checks/*rules.json` 为准, 增删规则后请同步更新本表。

---

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent; 安装/升级/禁用遥测的具体命令见 `references/cli-installation-guide.md`).

## Prerequisites

1. **Python 3.10+** — for the built-in skillspector and gitleaks checks
2. **Node.js + npx** — Optional; only needed for manual `markdownlint-cli2 --fix` during remediation
3. **hcloud CLI** — For Huawei Cloud service verification (optional, used in verification only)
4. **Huawei Cloud AK/SK** — Not required for audit itself, but needed if verifying skill functionality after audit

内置 / 外部二进制说明:
- **默认内置**: skillspector 与 gitleaks 均为纯 Python 实现, 无需外部二进制或 pip 安装。
- **外部路径显式指定才生效**: 传 `--skillspector`/`--gitleaks` `<path>` 时才使用外部二进制。
- **PATH 自动发现已禁用**(2026-09-23, fail-closed): 不再从 PATH 探测, 避免 PATH 被注入同名恶意二进制静默接管审计。
- **外部二进制不校验签名/哈希**: 请确保其来源可信(PATH 无同名二进制, 下载来源受控)。
- **默认行为**: 不传 `--skillspector`/`--gitleaks` 时, 恒使用内置纯 Python 实现, 与 scan level 无关。

To skip fallback auto-install of external binaries, use `--no-install` flag.

---
## Workflow

```
Input (skill path or folder)
    │
    ├── Discover Skills ──── Find SKILL.md in target or subdirectories
    │
    ├── Run Three Checks ────
    │   1. skillspector → AI security scan (52 rules, 609 patterns)
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
| `critical` | "critical" severity rules only (P5 harmful content) | Fast | Strictest gate |
| `high` | "critical" + "error" severity rules + AST (exec/eval/os.system/反序列化) | Fast | Block high-risk issues |
| `quick` | Pattern matching only (all static regex rules) | Fast | Quick pre-commit check |
| `standard` | All static analyzers (high 基础上放开 WARNING/INFO 级 AST + taint tracking) | Medium | CI/CD gate |
| `deep` | Standard + MCP analysis (least privilege, tool poisoning, rug pull) | Slower | Pre-release full audit |

> ⚠️ 术语区分: 扫描档位名(`critical`/`high`/`quick`/`standard`/`deep`, 反引号)与规则 JSON 中的
> severity 值("critical"/"high"/"medium"/"low", 引号)是**两套值** —— 档位决定启用哪些分析器并
> 过滤到哪些 severity 级别; severity 是单条规则的属性。同名不表示同一概念: 例如
> `critical` 档过滤出 "critical" 级发现, `high` 档过滤出 "critical"+"error" 级发现。

**Severity filtering applies only to SkillSpector** (rule selection per scan level). gitleaks bundles only "critical"/"high" severity rules, so all of them run at every scan level. runtime_security is level-independent: all 39 rules (36 CWE + Q001-Q003) always run, and its CRITICAL findings always block the gate.

**AST 分析在 high/standard/deep 均执行**(high 为默认档, 必须带 AST, 否则 eval/exec/pickle.loads 等执行类检测可被直接绕过)。high 档楼层过滤保留 CRITICAL/ERROR 级发现(critical/high 为规则 JSON 中的 severity 值, 内部映射为 CRITICAL/ERROR), 因此默认档阻断: AST1/2/5/9/10(exec/eval/os.system/getattr 反射/反序列化全部 ERROR 级); WARNING 级(AST3/4/6/7: compile/subprocess/动态 import 等)仅在 standard/deep 可见。.py 解析失败不再静默——产出 ERROR 级 AST-SYNTAX 发现并阻断 gate(fail-closed, 防恶意写坏代码规避 AST)。

---

## KooCLI Command Format Standard

This skill audits skill directories locally and does not directly invoke `hcloud` CLI commands.
When verifying a skill's functionality after audit, the standard KooCLI format applies — the line below is an **illustrative template, not a runnable command**:

```text
bash "$AUDIT_DIR/scripts/hcloud-run.sh" <Service> <Operation> --cli-region=<region> [--key=value ...]   # 强制入口：一切 hcloud 经 hcloud-run.sh 包装执行（hcloud-run.sh 内部自动经 skill-quality-cli run 包裹上报, 见 Step 0 强制要求）; hcloud 场景下用户只需调用 hcloud-run.sh, 不要手工再包一层 skill-quality-cli run
```

---

## Core Commands

> **⚠️ 安全要求(必须遵守)**: 所有命令必须通过 **绝对路径** 引用本 skill 的 `scripts/skill_audit.py`。
> 被审计的技能目录是**不可信输入** —— 其中可能被预置恶意 `scripts/skill_audit.py`, 若在
> 该目录内执行相对路径 `python3 scripts/skill_audit.py`, 审计会执行攻击者代码(RCE)。
> 执行前先设置 `AUDIT_DIR` 为本 skill(huawei-cloud-skill-audit)的安装目录绝对路径:
> `export AUDIT_DIR=/path/to/huawei-cloud-skill-audit`(示例: `$HOME/.local/share/huawei-cloud-skill-audit`)。
> 之后统一用 `python3 "$AUDIT_DIR/scripts/skill_audit.py" ...`, 并可用 `--target .` 指向你所在/任意被审计目录。
>
> **统一说明**: 每个场景给出两条命令 —— ① wrapped 命令(`skill-quality-cli run --skill-name huawei-cloud-skill-audit -- ...`): 正式使用必须用它(质量上报); ② 裸命令(`python3 "$AUDIT_DIR/scripts/skill_audit.py" ...`): 仅调试/离线场景的等效直接执行, 正式使用请勿用裸命令。

### Scan a single skill

```bash
# 先按上述安全要求设置 AUDIT_DIR, 然后在任意目录执行(--target . 指向被审计目录)
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .
```

### Scan a folder of skills

```bash
# --target 指向包含多个技能的父目录
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target ..
```

### Scan with specific level

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .. --scan-level quick
```

### Selective check execution

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .. --checks skillspector
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .. --skip-checks gitleaks
```

### Run with custom tool paths

Custom binary locations can be overridden with `--skillspector`, `--gitleaks` and `--node-bin` (see Parameter Confirmation; default auto-install location is `~/.local/bin/`):

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .. --skillspector /path/to/skillspector --gitleaks /path/to/gitleaks --node-bin /path/to/node
# 等效直接执行（⚠️ 仅调试/离线场景, 正式使用请经 skill-quality-cli run 包裹以保证质量上报）
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .. --skillspector /path/to/skillspector --gitleaks /path/to/gitleaks --node-bin /path/to/node
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
# CI 场景下 checkout 的仓库即本 skill 自身, 脚本来源可信, 相对路径无 RCE 风险
# (与 Core Commands 安全要求不冲突: 那里禁止的是在"被审计技能目录"内跑相对路径)
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

- `scripts/checks/skillspector_rules.json` — skillspector rules (52 rules / 609 patterns)
- `scripts/checks/gitleaks_rules.json` — gitleaks rules (43 rules)

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
| gitleaks (built-in) | 43 rules: API keys, passwords, private keys, tokens | Auto-installed |
| gitcode-security-scanner | Generic keyword credentials, Chinese keywords, SQL injection, debug leakage | From DTSE-SKILL repo |

**Recommended**: Run both `huawei-cloud-skill-audit` AND `gitcode-security-scanner` for complete coverage.

---

## Output Format

Report is a plain text file with four sections (Scanned Skills, Issue Summary, Issue Details, Fix Strategies) followed by a Gate Verdict (PASS/FAIL).

---

## Verification Method

### Run audit

```bash
# AUDIT_DIR 见 Core Commands 安全要求(本 skill 安装目录绝对路径)
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .
# 等效直接执行（⚠️ 仅调试/离线场景, 正式使用请经 skill-quality-cli run 包裹以保证质量上报）
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .
```

### Verify fix

```bash
# Fix issues from the report's Fix Strategies section, then re-run audit
skill-quality-cli run --skill-name huawei-cloud-skill-audit -- python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .
# 等效直接执行（⚠️ 仅调试/离线场景, 正式使用请经 skill-quality-cli run 包裹以保证质量上报）
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target .
```

### Check gate verdict

```bash
# Gate Verdict: PASS = 无 CRITICAL/ERROR 发现(WARNING 带记录理由后可接受)
# Gate Verdict: FAIL = 存在 CRITICAL 或 ERROR 发现(与 references/verification-method.md、security-audit-guide.md 一致)
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
| Built-in rules file missing | Check skipped with warning (built-in rules JSON is the only default path; external auto-download is not performed — fail-closed) |
| Python version < 3.12 | Built-in pure Python checks still work (Python 3.10+); external binaries not auto-detected (fail-closed), so no version-specific external fallback |
| Large repo produces huge report | Scan individual skills; use head/tail to read summary |
| gitleaks false positive | Add to .gitleaksignore file |
| skillspector exit code 1 | Findings reported per rule severity; risk score is display-only, not a gate condition |

---

## Design Principles

- **Three-Check Pipeline** — Each check is independent and contributes to the overall gate verdict
- **Auto-Install** — Missing tools are installed automatically on first run
- **Chain Verification** — All enabled checks must pass for gate verdict PASS
- **Agent-proof** — Write operations require user confirmation; automatic gate bypassing is not allowed
- **Data-Driven** — Report is structured text with clear severity levels and fix strategies
- **Batch Repeatable** — Same skill can be audited repeatedly; each run writes a fresh timestamped report
- **Credential Security** — No hardcoded AK/SK; read from environment variables
- **Least Privilege** — IAM policies follow minimum required permissions


