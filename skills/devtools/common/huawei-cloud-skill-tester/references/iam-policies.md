# IAM Policies

## Overview

The skill-tester framework requires read-only permissions for testing purposes. The specific IAM policies depend on the skill being tested.

## Minimum Required Permissions

For the tester framework itself:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:projects:list",
        "iam:users:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Per-Skill Permissions

Each skill under test may require additional IAM permissions. Refer to the individual skill's `references/iam-policies.md` for details.

## Security Note

- Always follow the principle of least privilege
- Use read-only permissions when possible
- Test credentials should be separate from production credentials
