# Verification Method — Huawei Cloud Skill Audit

## Audit Verification

### Run the five-check audit

```bash
python3 scripts/skill_audit.py --target /path/to/skill
```

### Verify each check individually

```bash
# skillcheck only
python3 scripts/skill_audit.py --target /path/to/skill --checks skillcheck

# markdownlint only
python3 scripts/skill_audit.py --target /path/to/skill --checks markdownlint

# skillspector only
python3 scripts/skill_audit.py --target /path/to/skill --checks skillspector

# hwcloud-spec only
python3 scripts/skill_audit.py --target /path/to/skill --checks hwcloud-spec

# gitleaks only
python3 scripts/skill_audit.py --target /path/to/skill --checks gitleaks
```

### Verify fix after remediation

```bash
# Step 1: Auto-fix markdownlint issues
markdownlint-cli2 "/path/to/skill/**/*.md" --config "/path/to/skill/.markdownlint.json" --fix

# Step 2: Fix non-auto-fixable issues manually (MD036, MD040, references.escape)

# Step 3: Re-run markdownlint --fix to catch new issues
markdownlint-cli2 "/path/to/skill/**/*.md" --config "/path/to/skill/.markdownlint.json" --fix

# Step 4: Re-run full audit
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
