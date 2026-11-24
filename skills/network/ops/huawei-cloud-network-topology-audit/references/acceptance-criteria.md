# Acceptance Criteria

## Functional Acceptance

| # | Criterion | Verification Method | Pass Condition |
|---|-----------|-------------------|----------------|
| 1 | SKILL.md exists | File exists | Verified |
| 2 | SKILL.md frontmatter has name, description, tags | `grep '^---$' SKILL.md` | Frontmatter complete |
| 3 | Overview section present | Section title match | Present |
| 4 | Prerequisites section present | Section title match | Present |
| 5 | Workflow section present (7 steps) | Section title match | Present |
| 6 | Core Commands section present | Section title match | Present |
| 7 | Parameter Confirmation section present | Section title match | Present |
| 8 | Quality Reporting section present | Section title match | Present |
| 9 | Reference Documents section present | Section title match | Present |
| 9a | KooCLI Command Format (Standard) section present | Section title match | Present |
| 9b | Examples section present | Section title match | Present |

## Structural Acceptance

| # | Criterion | File | Pass Condition |
|---|-----------|------|----------------|
| 10 | Rule directory exists | rules/network-audit-rules.yaml | Valid YAML, >= 30 rules |
| 11 | All required references exist | references/iam-policies.md | File exists |
| 12 | CLI installation guide exists | references/cli-installation-guide.md | File exists |
| 13 | Verification method exists | references/verification-method.md | File exists |
| 14 | Data flow diagram exists | references/dataflow-diagram.md | File exists |
| 15 | Precheck script exists | scripts/precheck.sh | Executable, bash |
| 16 | Rules validator exists | scripts/validate-rules.py | Python, syntax OK |
| 17 | Mermaid fallback exists | scripts/mermaid-to-ascii.sh | Executable, bash |
| 18 | DCS query script exists | scripts/query-dcs-instances.py | Python, syntax OK |
| 19 | Quality SDK exists | scripts/skill_quality_sdk.py | File exists |
| 19a | Quality reporting is opt-in | `SKILL_QUALITY_ENABLE` default | Disabled unless set to `1` |
| 19b | No TLS verification bypass | `grep -rn "verify_mode\|_create_unverified_context" scripts/` | No matches |
| 19c | Credential variable names consistent | SKILL.md / precheck.sh / query-dcs-instances.py | Same list and order |
| 19d | KooCLI commands carry `--cli-region` | Inspect SKILL.md + references | Every `hcloud` example has it |

## Validation Acceptance

| # | Criterion | Command | Pass Condition |
|---|-----------|---------|----------------|
| 20 | Rules pass validation | `python3 scripts/validate-rules.py rules/network-audit-rules.yaml` | Exit 0 |
| 21 | Precheck runs | `bash scripts/precheck.sh` | Exit 0 or clear error msg |
| 22 | SKILL.md <= 500 lines | `wc -l < SKILL.md` | <= 500 |
| 23 | Total files <= 30 | `find . -type f \| wc -l` | <= 30 |
| 24 | All file extensions in allowlist | Check each file | .md, .yaml, .py, .sh, .json |
| 25 | No credential hardcoding | `grep -rnE "AKIA[0-9A-Z]{16}\|access_key[[:space:]]*=[[:space:]]*[A-Z0-9]{16,}" .` | No matches |
| 26 | No plaintext token/password | `grep -rniE "password[[:space:]]*[:=]\|[[:space:]]*(token\|secret)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_-]{16,}" .` | Only placeholders/masked values |
| 27 | validate-rules.py exits non-zero without PyYAML | Run with PyYAML uninstalled | Readable error, exit 2, no traceback |
| 28 | query-dcs-instances.py exits 2 without credentials | Run with credentials unset | Readable error, exit 2 |