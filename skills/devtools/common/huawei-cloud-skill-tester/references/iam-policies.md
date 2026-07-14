# IAM Permission Policies

> Required API permission policies for huawei-cloud-skill-tester.

## Permission Overview

This Skill primarily executes Skill testing operations, involving the following permissions:

- Read Skill directories and files (local operation, no cloud API permission required)
- Execute hcloud CLI read-only operations to verify dependencies (requires basic query permission)
- Execute cloud API calls in test cases (depends on the tested Skill's permission requirements)

## Query Operation Permissions

| Service | Action | Description |
|---------|--------|-------------|
| IAM | iam:users:list | Verify authentication configuration |
| BSS | bss:order:list | Verify account status |

## Operation Permissions

This Skill itself does not require operation permissions. If test execution requires invoking the tested Skill's operations, permissions are defined by the tested Skill's `references/iam-policies.md`.

## Minimum Permission Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:users:list",
        "bss:order:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## MFA Requirements

| Operation | MFA Required |
|-----------|--------------|
| Read operations | No |
| Tested Skill operations | Per tested Skill definition |

## Notes

- When testing Skills in production, use an independent test account
- Ensure cleanup logic exists after tests involving create/delete resources
- Sensitive operation tests should run in dry-run mode
