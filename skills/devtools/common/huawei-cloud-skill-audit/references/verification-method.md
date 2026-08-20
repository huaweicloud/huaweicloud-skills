# Verification Method — Huawei Cloud Skill Audit

## Audit Verification

### Run the two-check audit

```bash
python3 scripts/skill_audit.py --target /path/to/skill
```

### Verify each check individually

```bash
# skillspector only
python3 scripts/skill_audit.py --target /path/to/skill --checks skillspector

# gitleaks only
python3 scripts/skill_audit.py --target /path/to/skill --checks gitleaks
```

### Verify fix after remediation

```bash
# Fix issues per the report's Fix Strategies, then re-run full audit
python3 scripts/skill_audit.py --target /path/to/skill
```

### Verify gate verdict

```bash
# Check the last line of the report
tail -5 skill-gate-report-*.txt

# Gate Verdict: PASS = all checks passed
# Gate Verdict: FAIL = one or more checks have issues
```

## Scan Level Verification

| Level | Command | Use Case |
|-------|---------|----------|
| quick | `--scan-level quick` | Pre-commit quick check |
| standard | `--scan-level standard` (default) | CI/CD gate |
| deep | `--scan-level deep` | Pre-release full audit |

## Environment Variables for AK/SK

The audit tool itself does not need AK/SK. If verifying skill functionality after audit:

Priority order:
1. `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
2. `HWC_AK` / `HWC_SK`
3. Prompt user for input
