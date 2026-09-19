# Security Audit Guide — Huawei Cloud Skill Audit

## Two-Check Security Audit

### 1. skillspector — AI Security Scanner

**What it checks (17 categories, 51 rules):**
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
- 42 credential rules (API keys, passwords, private keys, tokens)
- Generic API key format
- Private key format

**Common issues and fixes:**

| Issue | Fix |
|-------|-----|
| Hardcoded API key | Replace with `os.environ.get("VAR")` |
| Hardcoded private key | Load from file or secret manager; add to .gitignore |
| False positive | Add to `.gitleaksignore` |

## Remediation Priority

1. **CRITICAL** — Must fix before any release (credential leaks, reverse shells)
2. **ERROR** — Must fix before release (security patterns)
3. **WARNING** — Should fix; acceptable with documented justification

> Markdown style and SKILL.md spec compliance are NOT audited by this skill. Use external tooling (e.g. `markdownlint-cli2`, hwcloud-spec checks) separately if needed.
