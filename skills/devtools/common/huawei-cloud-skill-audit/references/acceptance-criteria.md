# Acceptance Criteria — Huawei Cloud Skill Audit

## Gate Verdict PASS Criteria

A Huawei Cloud skill passes the audit gate when **all five checks** report zero CRITICAL/ERROR issues:

| # | Check | PASS Criteria |
|---|-------|---------------|
| 1 | skillcheck | 0 errors; warnings acceptable |
| 2 | markdownlint-cli2 | 0 errors (all MD rules pass) |
| 3 | skillspector | Risk score <= 50; 0 critical/high findings |
| 4 | hwcloud-spec | All required frontmatter fields present; all required sections present; file size within limits |
| 5 | gitleaks | 0 credential leak findings |

## Acceptance Levels

| Level | Criteria | Action |
|-------|----------|--------|
| **PASS** | 0 CRITICAL, 0 ERROR | Skill is ready for release |
| **PASS with warnings** | 0 CRITICAL, 0 ERROR, >0 WARNING | Review warnings; skill may proceed |
| **FAIL** | Any CRITICAL or ERROR | Must fix before release |

## Per-Check Acceptance Details

### skillcheck

- `description.quality-score` >= threshold
- No `frontmatter.field.unknown` errors
- No `references.escape` errors (no `../` relative paths)

### markdownlint-cli2

- All MD rules pass after applying `.markdownlint.json` config
- Auto-fixable rules (MD022/MD031/MD032/MD047/MD012) must be fixed
- Non-auto-fixable rules (MD036/MD040) must be fixed manually

### skillspector

- No prompt injection patterns (P1-P5)
- No data exfiltration patterns (E1-E4)
- No privilege escalation patterns (PE1-PE3)
- No dangerous AST patterns (AST1-AST3)
- No YARA matches (YR1-YR4)
- No supply chain vulnerabilities (SC1-SC6)

### hwcloud-spec

- Frontmatter: name, description, tags fields present and valid
- name matches directory name
- tags count <= 5
- Required sections: Overview, Prerequisites, Core Commands, Parameter Confirmation, Reference Documents
- SKILL.md <= 500 lines
- Directory <= 5MB

### gitleaks

- No hardcoded API keys
- No hardcoded private keys
- No hardcoded passwords/tokens
- No credential patterns in any file
