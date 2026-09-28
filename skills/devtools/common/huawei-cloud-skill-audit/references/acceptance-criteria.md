# Acceptance Criteria — Huawei Cloud Skill Audit

## Gate Verdict PASS Criteria

A Huawei Cloud skill passes the audit gate when **all three checks** report zero CRITICAL/ERROR issues:

| # | Check | PASS Criteria |
|---|-------|---------------|
| 1 | skillspector | 0 CRITICAL/ERROR findings (不存在独立的 risk score 门禁: risk_score 仅作报告展示, 不参与 PASS/FAIL 判定) |
| 2 | gitleaks | 0 credential leak findings |
| 3 | runtime_security | 0 CRITICAL findings (36 CWE + Q001-Q003, 始终阻断 gate) |

## Acceptance Levels

| Level | Criteria | Action |
|-------|----------|--------|
| **PASS** | 0 CRITICAL, 0 ERROR (all three checks) | Skill is ready for release |
| **PASS with warnings** | 0 CRITICAL, 0 ERROR, >0 WARNING | Review warnings; skill may proceed |
| **FAIL** | Any CRITICAL or ERROR | Must fix before release |

## Per-Check Acceptance Details

### skillspector

- No prompt injection patterns (P1-P5)
- No data exfiltration patterns (E1-E5)
- No privilege escalation patterns (PE1-PE5)
- No ERROR-level dangerous AST patterns (AST1/2/5/9/10: exec/eval/os.system/getattr 反射/反序列化, 阻断 gate); 
  WARNING-level AST (AST3/4/6/7: compile/subprocess/动态 import) 仅 standard/deep 可见
- No YARA matches (YR1-YR4)
- No supply chain vulnerabilities (SC1/SC2/SC3/SC7)

### gitleaks

- No hardcoded API keys
- No hardcoded private keys
- No hardcoded passwords/tokens
- No credential patterns in any file
