# IAM Policies

This document describes the IAM permission policies required for the CES alarm automation skill.

## Required IAM Permissions

### Minimum Permission Requirements

To use this skill, the following IAM policies must be granted:

| Service | Policy Name | Scope | Description |
|---------|-------------|-------|-------------|
| CES | CES FullAccess | Region-level | Full access to Cloud Eye Service |
| ECS | ECS ReadOnlyAccess | Region-level | Read-only access to ECS instances |
| SMN | SMN FullAccess | Region-level | Full access to Simple Message Notification |

### Policy Description

**CES FullAccess**:

- Create alarm rules
- Query monitoring metrics
- Update alarm notification configuration
- List alarm rules and history

**ECS ReadOnlyAccess**:

- List ECS instances
- Query instance details
- Read instance metadata

**SMN FullAccess**:

- Create and manage SMN topics
- Subscribe/unsubscribe endpoints
- Send notifications

## Configuring IAM Policies

### Via Console

1. Log in to Huawei Cloud Console
2. Navigate to IAM > Users
3. Select target user or user group
4. Click "Add Permission"
5. Select policies:
   - CES FullAccess
   - ECS ReadOnlyAccess
   - SMN FullAccess
6. Confirm and save

### Via CLI

```bash
# Add CES FullAccess to user
hcloud IAM AttachGroupToUser --user-id=<user-id> --group-id=<ces-fullaccess-group-id>

# Add ECS ReadOnlyAccess to user
hcloud IAM AttachGroupToUser --user-id=<user-id> --group-id=<ecs-readonly-group-id>

# Add SMN FullAccess to user
hcloud IAM AttachGroupToUser --user-id=<user-id> --group-id=<smn-fullaccess-group-id>
```

## Custom Policy (Optional)

For more granular control, create a custom policy:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ces:CreateAlarm",
        "ces:UpdateAlarm",
        "ces:ListAlarms",
        "ces:ShowMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:listServers",
        "ecs:listServersDetails"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "smn:ListTopics",
        "smn:Subscribe",
        "smn:Unsubscribe"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Verification

After granting permissions, verify using:

```bash
# Verify CES access
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-4

# Verify ECS access
hcloud ECS ListServersDetails --cli-region=cn-north-4

# Verify SMN access
hcloud SMN ListTopics --cli-region=cn-north-4
```

If any command returns 403 Forbidden, check IAM policy configuration.

## Common Issues

### Issue 1: 403 Forbidden on CES Operations

**Solution**: Ensure CES FullAccess policy is granted to the user.

### Issue 2: 403 Forbidden on ECS Operations

**Solution**: Ensure ECS ReadOnlyAccess or ECS FullAccess policy is granted.

### Issue 3: 403 Forbidden on SMN Operations

**Solution**: Ensure SMN FullAccess policy is granted.

## References

- [Common Commands](common-commands.md)
- [IAM Official Documentation](https://support.huaweicloud.com/iam/index.html)
- [Policy Management](https://support.huaweicloud.com/usermanual-iam/iam_01_003.html)
