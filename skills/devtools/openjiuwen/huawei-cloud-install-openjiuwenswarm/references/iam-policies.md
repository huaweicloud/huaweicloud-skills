# IAM Policies

## Overview

IAM permissions required for this Skill at runtime.

## Permission List

### Required Permissions

| Permission Name | Permission Description | Usage Scenario |
|----------------|----------------------|----------------|
| `hwcloud:settings:read` | Read Huawei Cloud configuration file | Read API_BASE configuration |
| `keyring:read` | Read kernel keyring | Read API_KEY credential |

### Optional Permissions

| Permission Name | Permission Description | Usage Scenario |
|----------------|----------------------|----------------|
| `sys:mount` | File system mounting | Required for special deployment scenarios |

## Policy Example

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hwcloud:settings:read",
        "keyring:read"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Notes

1. **Principle of Least Privilege**: Grant only the minimum permissions required for operation
2. **Read-Only Permissions**: All permissions are read-only, no write operations involved
3. **Credential Protection**: API_KEY is read through the keyring, plaintext is not exposed