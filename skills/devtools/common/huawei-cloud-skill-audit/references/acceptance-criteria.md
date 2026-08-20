# Acceptance Criteria — Huawei Cloud Skill Audit

## Gate Verdict PASS Criteria

A Huawei Cloud skill passes the audit gate when **both checks** report zero CRITICAL/ERROR issues:

| # | Check | PASS Criteria |
|---|-------|---------------|
| 1 | skillspector | Risk score <= 50; 0 critical/high findings |
| 2 | gitleaks | 0 credential leak findings |

## Acceptance Levels

| Level | Criteria | Action |
|-------|----------|--------|
| **PASS** | 0 CRITICAL, 0 ERROR | Skill is ready for release |
| **PASS with warnings** | 0 CRITICAL, 0 ERROR, >0 WARNING | Review warnings; skill may proceed |
| **FAIL** | Any CRITICAL or ERROR | Must fix before release |

## Per-Check Acceptance Details

### skillspector

- No prompt injection patterns (P1-P5)
- No data exfiltration patterns (E1-E4)
- No privilege escalation patterns (PE1-PE3)
- No dangerous AST patterns (AST1-AST3)
- No YARA matches (YR1-YR4)
- No supply chain vulnerabilities (SC1-SC6)

### gitleaks

- No hardcoded API keys
- No hardcoded private keys
- No hardcoded passwords/tokens
- No credential patterns in any file
