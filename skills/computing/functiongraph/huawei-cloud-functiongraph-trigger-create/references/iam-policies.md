# IAM Policies for FunctionGraph Trigger Management

## Overview

This document specifies the minimum IAM (Identity and Access Management) permissions required to create and manage FunctionGraph scheduled triggers.

## Required Permissions

### Minimum Policy for Trigger Creation

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:get",
                "functiongraph:trigger:create",
                "functiongraph:trigger:list",
                "functiongraph:trigger:get"
            ],
            "Resource": [
                "urn:fss:*:*:function:*"
            ]
        }
    ]
}
```

### Full Trigger Management Policy

For complete trigger lifecycle management, use this policy:

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:get",
                "functiongraph:function:list",
                "functiongraph:trigger:create",
                "functiongraph:trigger:get",
                "functiongraph:trigger:list",
                "functiongraph:trigger:update",
                "functiongraph:trigger:delete"
            ],
            "Resource": [
                "urn:fss:*:*:function:*"
            ]
        }
    ]
}
```

## Permission Actions Reference

| Action | Description | Required For |
|--------|-------------|--------------|
| `functiongraph:function:get` | Query function details | Pre-check function existence |
| `functiongraph:function:list` | List all functions | Function discovery |
| `functiongraph:trigger:create` | Create trigger | **Core operation** |
| `functiongraph:trigger:get` | Query trigger details | Verification |
| `functiongraph:trigger:list` | List function triggers | Verification |
| `functiongraph:trigger:update` | Update trigger | Enable/disable trigger |
| `functiongraph:trigger:delete` | Delete trigger | Cleanup |

## Policy Assignment Methods

### Method 1: Through Console

1. Navigate to **IAM Console** → **Policies**
2. Click **Create Custom Policy**
3. Select **JSON** view
4. Paste the policy JSON
5. Click **OK** to create
6. Attach policy to user/group/role

### Method 2: Using KooCLI

```bash
# Create policy
hcloud iam v3 create-custom-policy \
    --body '{
        "policy": {
            "name": "FunctionGraphTriggerManager",
            "description": "Policy for managing FunctionGraph triggers",
            "policy_document": {
                "Version": "1.1",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["functiongraph:trigger:create"],
                        "Resource": ["urn:fss:*:*:function:*"]
                    }
                ]
            }
        }
    }'
```

### Method 3: Assign to User

```bash
# Attach policy to user
hcloud iam v3 attach-user-policy \
    --user-id "user-xxx" \
    --policy-id "policy-xxx"
```

## Resource Scoping

### All Functions in All Regions

```json
"Resource": ["urn:fss:*:*:function:*"]
```

### Specific Region

```json
"Resource": ["urn:fss:cn-north-4:*:function:*"]
```

### Specific Function

```json
"Resource": [
    "urn:fss:cn-north-4:project-id:function:default:my-function:*"
]
```

### Multiple Specific Functions

```json
"Resource": [
    "urn:fss:cn-north-4:project-id:function:default:backup-function:*",
    "urn:fss:cn-north-4:project-id:function:default:cleanup-function:*"
]
```

## Condition Keys

Use conditions to further restrict access:

### Time-based Restriction

```json
{
    "Effect": "Allow",
    "Action": ["functiongraph:trigger:create"],
    "Resource": ["*"],
    "Condition": {
        "DateLessThan": {
            "g:CurrentTime": "2024-12-31T23:59:59Z"
        }
    }
}
```

### Source IP Restriction

```json
{
    "Effect": "Allow",
    "Action": ["functiongraph:trigger:create"],
    "Resource": ["*"],
    "Condition": {
        "IpAddress": {
            "g:SourceIp": ["192.168.1.0/24", "10.0.0.0/8"]
        }
    }
}
```

## Role-Based Access Control (RBAC)

### Built-in Roles

| Role | Description | Includes Trigger Permissions |
|------|-------------|----------------------------|
| `Tenant Administrator` | Full access | Yes |
| `FunctionGraph Administrator` | FunctionGraph full access | Yes |
| `FunctionGraph Developer` | Create/manage functions | Yes |
| `FunctionGraph Viewer` | Read-only access | No (view only) |

### Custom Role for Automation

For CI/CD pipelines and automation:

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:get",
                "functiongraph:trigger:create",
                "functiongraph:trigger:list"
            ],
            "Resource": ["urn:fss:*:*:function:*"]
        }
    ]
}
```

## Verifying Permissions

### Check User Permissions

```bash
# List user's policies
hcloud iam v3 list-user-permissions --user-id "user-xxx"

# Check specific permission
hcloud functiongraph v2 list-functions --limit 1
```

### Permission Testing Script

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient

def test_permission():
    credentials = BasicCredentials(
        ak=os.environ.get('HUAWEI_AK'),
        sk=os.environ.get('HUAWEI_SK'),
        project_id=os.environ.get('HUAWEI_PROJECT_ID')
    )
    
    client = FunctionGraphClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(FunctionGraphRegion.value_of(os.environ.get('HUAWEI_REGION'))) \
        .build()
    
    try:
        # Test list functions (requires functiongraph:function:list)
        response = client.list_functions(limit=1)
        print("✓ Has function list permission")
        
        # Additional tests can be added here
        
    except Exception as e:
        print(f"✗ Permission denied: {e}")

test_permission()
```

## Permission Troubleshooting

### Error: 403 Forbidden

**Cause**: Missing required IAM permission

**Solution**:

1. Check if `functiongraph:trigger:create` is in policy
2. Verify policy is attached to user/role
3. Check resource scope matches target function

### Error: Unauthorized

**Cause**: Invalid or expired credentials

**Solution**:

1. Verify AK/SK are correct
2. Check if credentials have been rotated
3. Re-configure KooCLI authentication

## Security Best Practices

1. **Principle of Least Privilege**: Grant only required permissions
2. **Use Resource Restrictions**: Limit to specific functions/regions
3. **Add Conditions**: Restrict by IP, time, or MFA
4. **Separate Environments**: Use different policies for dev/prod
5. **Regular Audits**: Review and remove unused permissions
6. **Temporary Credentials**: Use STS for short-lived access

## Policy Examples by Use Case

### Development Environment

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:*"
            ],
            "Resource": ["urn:fss:cn-north-4:*:function:dev-*:*"]
        }
    ]
}
```

### Production Environment (Restricted)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:get",
                "functiongraph:trigger:get",
                "functiongraph:trigger:list"
            ],
            "Resource": ["urn:fss:cn-north-4:*:function:prod-*:*"]
        }
    ]
}
```

### CI/CD Pipeline

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:get",
                "functiongraph:trigger:create",
                "functiongraph:trigger:update",
                "functiongraph:trigger:delete"
            ],
            "Resource": ["urn:fss:*:*:function:*"],
            "Condition": {
                "StringEquals": {
                    "g:UserName": "cicd-service-account"
                }
            }
        }
    ]
}
```

## Related Documentation

- [IAM Policy Syntax](https://support.huaweicloud.com/usermanual-iam/iam_01_001.html)
- [FunctionGraph Permissions](https://support.huaweicloud.com/productdesc-functiongraph/functiongraph_01_0024.html)
- [Best Practices](https://support.huaweicloud.com/bestpractice-iam/bestpractice_0001.html)
