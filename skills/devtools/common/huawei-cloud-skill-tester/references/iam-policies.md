# IAM Policies — huawei-cloud-skill-tester

## Overview

The skill-tester framework itself does not require specific IAM permissions. However, it executes test cases against real Huawei Cloud environments for the skills under test. The IAM permissions required depend entirely on the APIs and operations invoked by the skill being tested.

## Required Permissions

### For the Skill Tester Framework

| Permission | Description | Scope |
|------------|-------------|-------|
| None | The tester runs locally and orchestrates scripts; no direct Huawei Cloud API calls | N/A |

### For Skills Under Test

Each skill under test may require different IAM permissions. Refer to the skill-specific `references/iam-policies.md` for details. Common permission categories include:

| Category | Common Actions |
|----------|---------------|
| Read-Only | `Show*`, `List*`, `Get*`, `Describe*` |
| Write | `Create*`, `Update*`, `Delete*`, `Attach*`, `Detach*` |

## Policy Examples

### Read-Only Test Policy

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ECS:List*",
        "ECS:Show*",
        "ECS:Get*",
        "VPC:List*",
        "VPC:Show*",
        "OBS:List*",
        "OBS:Get*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### Read-Write Test Policy (for full E2E testing)

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ECS:*",
        "VPC:*",
        "OBS:*",
        "EVS:*",
        "EIP:*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Credential Requirements

The tester reads credentials from environment variables:

- `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
- or `HWC_AK` / `HWC_SK`

**Important:**
- Use a dedicated IAM user with narrowly scoped permissions for testing
- Never use the account-level access key
- If AK/SK is missing, the tester will prompt the user to provide them before execution
