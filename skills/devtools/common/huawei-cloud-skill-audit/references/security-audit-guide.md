# Security Audit Guide — Huawei Cloud Skill Audit

## Three-Check Security Audit

### 1. skillspector — AI Security Scanner

**What it checks (18 categories, 52 rules; 编号含预留位, 以 `skillspector_rules.json` 为准):**
- Prompt injection / system prompt leakage (P1-P8)
- Data exfiltration (E1-E5)
- Privilege escalation (PE1-PE5)
- Behavioral AST (AST1-AST7/9/10)
- YARA patterns (YR1-YR4)
- Supply chain (SC1/SC2/SC3/SC7)
- Excessive agency (EA1-EA4), memory poisoning (MP1-MP3), output handling (OH1-OH3)
- Rogue agent (RA1-RA2), agent snooping (AS1-AS3)
- Server-side request forgery (SSRF1-SSRF3), tool misuse (TM1-TM4)

**Common issues and fixes:**

| Category | Fix |
|----------|-----|
| Prompt injection | Use template variables; sanitize user input |
| Data exfiltration | Remove external URLs; use env vars for endpoints |
| Privilege escalation | Avoid sudo/root; use capability-based permissions |
| Dangerous AST | Replace exec()/eval() with safer alternatives |
| YARA matches | Remove reverse shell/webshell patterns |
| Supply chain | Pin dependency versions with hashes |

### 2. gitleaks — Credential Leak Detection

**What it checks:**
- 43 credential rules (API keys, passwords, private keys, tokens)
- Generic API key format
- Private key format

**Common issues and fixes:**

| Issue | Fix |
|-------|-----|
| Hardcoded API key | Replace with `os.environ.get("VAR")` |
| Hardcoded private key | Load from file or secret manager; add to .gitignore |
| False positive | Add to `.gitleaksignore` |

### 3. runtime_security — CWE High-Risk Runtime Patterns

**What it checks (36 CWE rules + 3 skill-quality rules Q001-Q003):**
- Command injection / shell injection (CMD002, INJ001)
- Unsafe deserialization / sandbox escape (INJ002, INJ001-class-bases)
- Credential theft (~/.ssh file reads, env var harvesting)
- Persistence, destructive ops, mining (logic bombs, LD_PRELOAD)
- Level-independent: all 39 rules always run at every scan level; CRITICAL findings always block the gate.

**Common issues and fixes:**

| Issue | Fix |
|-------|-----|
| Command injection (os.system / shell -c) | Use subprocess with explicit arg lists, never shell strings |
| Unsafe deserialization | Prefer safe literal parsing (ast.literal_eval) over pickle/yaml.load |
| Credential theft | Read secrets from env vars / secret manager, not files |
| Sandbox escape chains | Avoid `__class__.__bases__` traversal; run untrusted code in isolated sandbox |
| Logic bombs / obfuscation | Remove time-bomb or encoded payload patterns; review dependencies |

## Remediation Priority

1. **CRITICAL** — Must fix before any release (credential leaks, reverse shells)
2. **ERROR** — Must fix before release (security patterns)
3. **WARNING** — Should fix; acceptable with documented justification

> Markdown style and SKILL.md spec compliance are NOT audited by this skill. Use external tooling (e.g. `markdownlint-cli2`, hwcloud-spec checks) separately if needed.
