# IAM Policies — Huawei Cloud Skill Audit

## Required IAM Permissions

The audit tool itself does **not** require Huawei Cloud IAM permissions. It operates entirely on local files (SKILL.md, scripts, references).

However, if you want to **verify a skill's functionality** after audit (e.g., test that CLI commands work), the following permissions may be needed:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:credentials:list"
      ]
    }
  ]
}
```

## Audited Skill IAM Policies

When auditing a Huawei Cloud skill, the audit checks that the skill's own `references/iam-policies.md` exists and follows the least privilege principle.

### Audit Checks on IAM

| Check | Tool | What It Verifies |
|-------|------|-----------------|
| references/iam-policies.md exists | hwcloud-spec | File must exist in the skill directory |
| No wildcard permissions | skillspector | No `*:*` or overly broad actions |
| No hardcoded AK/SK | gitleaks | No credential strings in source files |
| No sudo/root commands | skillspector | No privilege escalation patterns |

## Least Privilege Principle

- Each skill should only have the minimum permissions required for its operations
- Read operations (List/Show/Get) and write operations (Create/Update/Delete) should be listed separately
- IAM policies must use JSON format with policy descriptions
