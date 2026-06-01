# IAM Policies for FunctionGraph

This document defines the required IAM (Identity and Access Management) policies for creating and managing Huawei Cloud FunctionGraph functions.

## Required Permissions

### Core Permissions for Function Creation

| Permission | Description | Action Type |
|------------|-------------|-------------|
| functiongraph:function:create | Create a new function | Write |
| functiongraph:function:list | List functions in a project | List |
| functiongraph:function:get | Get function details | Read |
| functiongraph:function:update | Update function configuration | Write |
| functiongraph:function:delete | Delete a function | Write |

### Additional Permissions for Deployment

| Permission | Description | Action Type |
|------------|-------------|-------------|
| functiongraph:function:invoke | Invoke a function | Write |
| functiongraph:alias:create | Create function alias | Write |
| functiongraph:alias:list | List function aliases | List |
| functiongraph:version:list | List function versions | List |
| functiongraph:trigger:create | Create trigger for function | Write |
| functiongraph:trigger:list | List function triggers | List |

## Policy Templates

### Full Access Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:*:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Function Creation Policy (Minimum Required)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:create",
        "functiongraph:function:list",
        "functiongraph:function:get",
        "functiongraph:function:update"
      ],
      "Resource": [
        "urn:fg:*:*:function:*"
      ]
    }
  ]
}
```

### Resource-Specific Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:create",
        "functiongraph:function:get",
        "functiongraph:function:update",
        "functiongraph:function:invoke"
      ],
      "Resource": [
        "urn:fg:cn-north-4:*:function:my-function-*"
      ],
      "Condition": {
        "StringEquals": {
          "fg:app_id": "app-12345678"
        }
      }
    }
  ]
}
```

## Policy Application Methods

### Method 1: Console-Based Configuration

1. Log in to Huawei Cloud Console
2. Navigate to **Identity and Access Management** > **Policies**
3. Click **Create Custom Policy**
4. Select **JSON** view and paste policy document
5. Click **OK** to create the policy
6. Attach policy to user or group

### Method 2: KooCLI-Based Configuration

```bash
# Create custom policy
hcloud IAM policy create \
  --cli-region=cn-north-4 \
  --body='{
    "policy": {
      "name": "FunctionGraphCreatePolicy",
      "description": "Policy for creating FunctionGraph functions",
      "policy_document": {
        "Version": "1.1",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "functiongraph:function:create",
              "functiongraph:function:list",
              "functiongraph:function:get"
            ],
            "Resource": "*"
          }
        ]
      }
    }
  }'

# Attach policy to user
hcloud IAM user attach-policy \
  --user_id=USER_ID \
  --policy_id=POLICY_ID
```

## Cross-Service Permissions

FunctionGraph may require permissions for other services:

| Service | Required Permission | Purpose |
|---------|---------------------|---------|
| OBS | obs:bucket:get, obs:object:get | Reading function code packages |
| VPC | vpc:vpc:get, vpc:subnet:get | VPC configuration for functions |
| DIS | dis:stream:put | DIS trigger integration |
| APIG | apig:api:create | API Gateway trigger creation |
| LTS | lts:log:create | Log transmission to LTS |

### Cross-Service Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:*",
        "obs:bucket:get",
        "obs:object:get",
        "vpc:vpc:get",
        "vpc:subnet:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Verification

### Verify Current User Permissions

```bash
# List attached policies
hcloud IAM user list-policies --user_name=YOUR_USERNAME

# Test FunctionGraph access
hcloud FunctionGraph function list --cli-region=cn-north-4

# Attempt to create test function (dry-run)
hcloud FunctionGraph function create \
  --cli-region=cn-north-4 \
  --func_name=permission-test \
  --package_type=Zip \
  --runtime=Python3.9 \
  --handler=index.handler \
  --memory_size=128 \
  --timeout=10
```

## Permission Scopes

### Project-Level Scope

Policies applied at project level only affect resources within that project:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:*"
      ],
      "Resource": "*",
      "Scope": {
        "Project": [
          "cn-north-4"
        ]
      }
    }
  ]
}
```

### Domain-Level Scope

Policies applied at domain level affect all projects:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Best Practices

| Practice | Description |
|----------|-------------|
| Least Privilege | Grant only minimum required permissions |
| Resource Restrictions | Use specific resource URNs instead of wildcards |
| Condition Keys | Apply conditions for additional constraints |
| Regular Audits | Review and remove unused permissions |
| Separate Environments | Use different policies for dev/test/prod |

## Troubleshooting Permission Issues

### Common Errors

| Error Code | Message | Solution |
|------------|---------|----------|
| 403 | Permission denied | Add required permission to policy |
| 403 | User has no permission to access resource | Check resource-level permissions |
| 403 | Cross-project access denied | Verify project-level scope |

### Diagnostic Steps

```bash
# Check user information
hcloud IAM user show --user_name=YOUR_USERNAME

# Verify policy attachments
hcloud IAM policy list-attachments --policy_id=POLICY_ID

# Enable debug mode for detailed error
hcloud --debug FunctionGraph function create --func_name=test
```

## Related Documentation

- [Huawei Cloud IAM Documentation](https://support.huaweicloud.com/intl/en-us/productdesc-iam/iam_01_0001.html)
- [FunctionGraph API Permissions](https://support.huaweicloud.com/intl/en-us/api-functiongraph/functiongraph_06_0101.html)
- [Custom Policy Syntax](https://support.huaweicloud.com/intl/en-us/usermanual-iam/iam_01_0017.html)
