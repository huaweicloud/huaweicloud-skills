# IAM Policies

## Overview

This skill requires specific IAM permissions. Ensure your account has the following permissions.

## Required Permissions

### Flexus L Permissions

> **Note:** Flexus L uses ECS service internally, so ECS permissions are required.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:servers:get",
        "ecs:servers:start",
        "ecs:servers:stop",
        "ecs:servers:reboot",
        "ecs:serverPasswords:reset"
      ]
    }
  ]
}
```

### BSS Permissions (Traffic Query)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:resourceUsage:get"
      ]
    }
  ]
}
```

## Permission Configuration Steps

### Step 1: Create Custom Policy

1. Login to Huawei Cloud Console
2. Go to IAM Console
3. Select "Permission Management" → "Custom Policies"
4. Click "Create Custom Policy"
5. Enter policy name (e.g., FlexusL-Ops-Policy)
6. Select "JSON" view
7. Paste the above permission policy
8. Click "OK"

### Step 2: Attach Policy to User

1. Go to IAM Console
2. Select "Users" → Find target user
3. Click "Authorize"
4. Select the custom policy just created
5. Click "OK"

## Permission Verification

### Verify ECS Permissions

```bash
python3 {baseDir}/scripts/cli.py test
```

### Insufficient Permission Handling

If permission denied:
1. Check if IAM policy is correctly attached to user
2. Verify AK/SK is valid
3. Confirm region configuration is correct
4. Check ErrorCode in error message

## Least Privilege Principle

Follow the least privilege principle: only grant necessary permissions, avoid granting excessive permissions.
