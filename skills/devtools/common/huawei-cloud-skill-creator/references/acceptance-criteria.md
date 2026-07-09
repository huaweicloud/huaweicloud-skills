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

## Acceptance Workflow

1. Run `bash scripts/validate-skill.sh {skill-path}` for automated checks
2. Confirm output Grade is A or B
3. Manual review of content quality (example accuracy, step completeness)
4. If scripts exist, test script executability
5. All pass → acceptance complete

## Acceptance Rating

| Rating | Condition | Follow-up Action |
|--------|-----------|-----------------|
| Pass | Grade A/B + manual review passed | Ready to publish |
| Conditional pass | Grade B + some recommended items not met | Publishable, create improvement Issue |
| Fail | Grade C/D or manual review not passed | Must fix and re-accept |
