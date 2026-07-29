# Security Audit Guide — Huawei Cloud Skill Audit

## Five-Check Security Audit

### 1. skillcheck — SKILL.md Spec Validation

**What it checks:**
- Frontmatter fields (name, description, tags, version)
- Description quality (action verb, trigger context)
- Reference safety (no `../` escape paths)
- Metadata budget (token count)

**Common issues and fixes:**

| Issue | Fix |
|-------|-----|
| description.quality-score low | Start with action verb; add "Use this skill whenever..." |
| references.escape | Replace `[text](../other-skill/SKILL.md)` with `[text (other-skill-name)]` |
| frontmatter.field.unknown | Add to skillcheck.toml extension_fields or remove |

### 2. markdownlint-cli2 — Markdown Style

**What it checks:**
- Line length, blank lines around code blocks
- Duplicate headings, emphasis as heading
- List indentation, code block language tags

**Fix strategy:**
1. Run `markdownlint-cli2 --fix` first (handles most issues)
2. Manually fix MD036 (emphasis-as-heading) and MD040 (missing language tag)
3. Re-run `--fix` to catch new issues from manual edits

### 3. skillspector — AI Security Scanner

**What it checks (17 categories, 68 patterns):**
- Prompt injection (P1-P5)
- Data exfiltration (E1-E4)
- Privilege escalation (PE1-PE3)
- Behavioral AST (AST1-AST3)
- YARA patterns (YR1-YR4)
- Supply chain (SC1-SC6)
- MCP analysis (LP1-LP4, TP1-TP4) — deep scan only

**Common issues and fixes:**

| Category | Fix |
|----------|-----|
| Prompt injection | Use template variables; sanitize user input |
| Data exfiltration | Remove external URLs; use env vars for endpoints |
| Privilege escalation | Avoid sudo/root; use capability-based permissions |
| Dangerous AST | Replace exec()/eval() with safer alternatives |
| YARA matches | Remove reverse shell/webshell patterns |
| Supply chain | Pin dependency versions with hashes |

### 4. hwcloud-spec — Huawei Cloud Spec

**What it checks:**
- Frontmatter required fields (name, description, tags)
- Frontmatter recommended fields (version)
- Section structure (required: Overview, Prerequisites, Core Commands, Parameter Confirmation, Reference Documents)
- File size limits (SKILL.md <= 500 lines, dir <= 5MB)

**Common issues and fixes:**

| Issue | Fix |
|-------|-----|
| Missing frontmatter field | Add the required field |
| name mismatch | Set name to match directory name |
| Missing required section | Add the section with appropriate content |
| File too large | Split content into references/ |

### 5. gitleaks — Credential Leak Detection

**What it checks:**
- 800+ credential patterns (API keys, passwords, private keys, tokens)
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
2. **ERROR** — Must fix before release (spec violations, security patterns)
3. **WARNING** — Should fix; acceptable with documented justification
