# Acceptance Criteria

> Read this file when determining whether a Skill development task is complete.

## Acceptance Conditions

A Skill must satisfy all of the following conditions to pass acceptance:

### Structural Acceptance

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| SKILL.md exists | File exists and is non-empty | `test -s SKILL.md` |
| Frontmatter complete | name + description required | `validate-skill.sh` |
| Directory structure complete | references/ exists | `test -d references/` |
| Naming convention | Follows `{platform}-{product}-{function}` | Regex match |

### Content Acceptance

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| description structured | Contains 5 numbered points | Check `1.` `2.` `3.` |
| Overview section | Contains background and positioning | Check `## Overview` |
| Main steps | Each step has CLI commands | Check code blocks |
| Usage examples | 3-5 typical examples | Count `### Example` |
| Permission annotations | Each operation notes required permissions | Check `Required permission` |

### Security Acceptance

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| No hardcoded AK/SK | No plaintext credentials in SKILL.md or scripts | `validate-skill.sh` security check |
| Env var retrieval | Secrets obtained via `${VAR}` | grep check |
| Write confirmation | Create/update/delete operations have confirmation prompt | Check body description |
| dry-run | High-risk operations have preview mode documentation | Check `--dry-run` |

### Permission Acceptance

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| iam-policies.md | File exists | `test -f references/iam-policies.md` |
| Query/mutation separated | Two operation types listed separately | Check section headers |
| Minimum privilege JSON | Contains policy JSON | Check `json` code block |
| MFA annotation | High-risk operations note MFA requirement | Check MFA column |

### Documentation Acceptance

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| references links valid | All referenced files exist | `validate-skill.sh` |
| ref files focused | Each ref solves one problem | Manual review |
| ref files have header | First line explains when to read | Manual review |
| Code blocks annotated | All code blocks have language identifier | Check ` ```bash ` etc. |

### i18n Acceptance (Recommended)

|| Condition | Criterion | Verification Method |
||-----------|-----------|---------------------|
|| i18n/ directory | Directory exists | `test -d i18n/` |
|| zh-CN locale | `i18n/zh-CN/` directory exists | `test -d i18n/zh-CN/` |
|| SKILL_CN.md | File exists with valid Frontmatter | `validate-skill.sh` i18n check |
|| Chinese description | description field written in Chinese | Check for Chinese characters |
|| Chinese trigger words | Contains "触发场景包括" | grep check |
|| CLI not translated | Commands remain in English | `grep -E 'hcloud [A-Z]+' SKILL_CN.md` |

### Functional Testing

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| CLI syntax verified | All commands pass `--help` | `bash scripts/test-cli-commands.sh` |
| Read-only ops tested | Live query with `--limit=1` | Check test report |
| Reboot verified via --help | Not executed live | Check test report |
| Test report exists | `references/test-report.md` generated | `test -f references/test-report.md` |

### Resource Lifecycle Testing (if skill creates/destroys resources)

| Condition | Criterion | Verification Method |
|-----------|-----------|---------------------|
| Test plan described | User shown what resources will be created | Review conversation |
| Credentials confirmed | User provided AKSK or explicitly declined | Review conversation |
| Resource created | Test resource created with minimum spec | Check test report |
| Resource released | Test resource deleted after testing | Check test report |
| Cleanup guaranteed | Resources released even on test failure | Review conversation |
| Report updated | Resource lifecycle section in test-report.md | Check test report |

### Semantic Validation Acceptance

|| Condition | Criterion | Verification Method |
||-----------|-----------|---------------------|
|| Field semantics verified | Returned field names match intended meaning | Review live query output |
|| Ambiguity resolved | Ambiguous fields cross-referenced or user confirmed | Review conversation |
|| Plausibility checked | Numeric values pass order-of-magnitude sanity check | Review live query output |
|| Correct field used | Generated Skill uses confirmed field name | Check SKILL.md |
|| Semantic note added | SKILL.md documents field meaning for ambiguous cases | Check SKILL.md body |

## Acceptance Workflow

1. Run `bash scripts/validate-skill.sh {skill-path}` for automated checks
2. Confirm output Grade is A or B
3. Manual review of content quality (example accuracy, step completeness)
4. If scripts exist, test script executability
5. Perform functional testing (CLI `--help` verification, read-only live tests, credential notice)
6. Perform semantic validation on financial/usage/metric data (check field meaning, resolve ambiguity, confirm with user if needed)
7. Confirm `references/test-report.md` exists with tests results
8. All pass → acceptance complete

## Acceptance Rating

| Rating | Condition | Follow-up Action |
|--------|-----------|-----------------|
| Pass | Grade A/B + manual review passed | Ready to publish |
| Conditional pass | Grade B + some recommended items not met | Publishable, create improvement Issue |
| Fail | Grade C/D or manual review not passed | Must fix and re-accept |
