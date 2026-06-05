# IAM Policies for Huawei Cloud ECS Monitoring

## Overview

This document outlines the Identity and Access Management (IAM) policies and permissions
required for the Huawei Cloud ECS Monitoring skill. Proper IAM configuration ensures
secure and controlled access to Huawei Cloud resources.

## Required IAM Permissions Matrix

### Read-Only Permissions - Monitoring and Viewing

| API Action | Permission | Purpose |
|------------|------------|---------|
| `ecs:cloudServers:get` | View instance details | Get instance detailed information |
| `ecs:cloudServers:list` | View instance list | List all ECS instances |
| `vpc:securityGroups:get` (Optional) | View security groups | View security group configuration |
| `ces:metrics:list` | View metric list | List available monitoring metrics |
| `ces:metricData:get` | View metric data | Get historical monitoring data |

### Read-Write Permissions - Management and Operations (Optional)

| API Action | Permission | Purpose |
|------------|------------|---------|
| `ecs:cloudServers:remoteConsole` (Optional) | Get VNC console | Access via VNC when SSH fails |
| `ecs:cloudServers:action` (Optional) | Instance operations | Start/stop/restart instances |

## Detailed Permission Requirements

### Minimum Required Permissions

The skill requires the following IAM permissions to function properly:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ces:metrics:list",
        "ces:metricData:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### Recommended Permissions (Full Access)

For full functionality, including alarm management and advanced features:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        // ECS Permissions
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ecs:cloudServers:action",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudServerImages:list",
        
        // CES Permissions
        "ces:metrics:list",
        "ces:metricData:get",
        "ces:alarms:list",
        "ces:alarms:get",
        "ces:alarmTemplates:list",
        "ces:alarmTemplates:get",
        "ces:alarmRules:list",
        "ces:alarmRules:get",
        
        // IAM Permissions (for credential verification)
        "iam:users:getUser",
        "iam:users:listUsers",
        "iam:permissions:listPermissionsForUser"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Failure Handling Process (MUST)

### Permission Check Failure Handling

When any operation encounters a permission error failure, MUST follow this process:

1. **Identify permission error**
   - Check if error message contains keywords like "Access denied", "Insufficient permissions", "User does not have permission"
   - Confirm if error is related to IAM permissions

2. **Refer to permission documentation**
   - Immediately guide user to view `references/iam-policies.md` file
   - Provide specific permission requirements explanation

3. **Display permission list**
   - Show user the required permission list and corresponding JSON policy
   - Explain the purpose and necessity of each permission

4. **Guide permission configuration**
   - Guide user to create custom policy in Huawei Cloud IAM console
   - Provide specific operation steps:
     a. Log in to Huawei Cloud Console
     b. Navigate to IAM service
     c. Create custom policy
     d. Copy the provided JSON policy
     e. Assign policy to user/user group

5. **Pause execution and wait for confirmation**
   - Pause current operation execution
   - Wait for user to confirm permission configuration is complete
   - Provide verification commands for user to test permissions

## Permission Details

### ECS (Elastic Cloud Server) Permissions

#### 1. **ecs:cloudServers:list**

- **Description**: List ECS instances
- **Required for**: Listing available instances
- **API Operation**: `GET /v1/{project_id}/cloudservers`
- **Use Case**: User wants to see all ECS instances

#### 2. **ecs:cloudServers:get**

- **Description**: Get ECS instance details
- **Required for**: Getting instance metadata
- **API Operation**: `GET /v1/{project_id}/cloudservers/{server_id}`
- **Use Case**: User selects a specific instance for monitoring

#### 3. **ecs:cloudServers:action** (Optional)

- **Description**: Perform actions on ECS instances
- **Required for**: Restarting, stopping, starting instances
- **API Operation**: `POST /v1/{project_id}/cloudservers/action`
- **Use Case**: Troubleshooting requires instance restart

#### 4. **ecs:cloudServerFlavors:list** (Optional)

- **Description**: List available ECS flavors
- **Required for**: Understanding instance specifications
- **API Operation**: `GET /v1/{project_id}/cloudservers/flavors`
- **Use Case**: Comparing instance performance metrics

#### 5. **ecs:cloudServerImages:list** (Optional)

- **Description**: List available images
- **Required for**: Instance configuration context
- **API Operation**: `GET /v1/{project_id}/cloudimages`
- **Use Case**: Understanding OS and application context

### CES (Cloud Eye Service) Permissions

#### 1. **ces:metrics:list**

- **Description**: List available metrics
- **Required for**: Discovering what metrics are available
- **API Operation**: `GET /V1.0/{project_id}/metrics`
- **Use Case**: User wants to see all monitorable metrics

#### 2. **ces:metricData:get**

- **Description**: Get metric data
- **Required for**: Querying monitoring data
- **API Operation**: `POST /V1.0/{project_id}/metric-data`
- **Use Case**: Core monitoring functionality

#### 3. **ces:alarms:list** (Optional)

- **Description**: List alarms
- **Required for**: Showing existing alarms
- **API Operation**: `GET /V1.0/{project_id}/alarms`
- **Use Case**: User wants to see current alarms

#### 4. **ces:alarms:get** (Optional)

- **Description**: Get alarm details
- **Required for**: Showing alarm configuration
- **API Operation**: `GET /V1.0/{project_id}/alarms/{alarm_id}`
- **Use Case**: Troubleshooting specific alarms

#### 5. **ces:alarmTemplates:list** (Optional)

- **Description**: List alarm templates
- **Required for**: Suggesting alarm configurations
- **API Operation**: `GET /V1.0/{project_id}/alarm-templates`
- **Use Case**: User wants to create new alarms

#### 6. **ces:alarmTemplates:get** (Optional)

- **Description**: Get alarm template details
- **Required for**: Template-based alarm creation
- **API Operation**: `GET /V1.0/{project_id}/alarm-templates/{template_id}`
- **Use Case**: Applying predefined alarm templates

#### 7. **ces:alarmRules:list** (Optional)

- **Description**: List alarm rules
- **Required for**: Showing alarm rule configurations
- **API Operation**: `GET /V1.0/{project_id}/alarm-rules`
- **Use Case**: Reviewing alarm configurations

#### 8. **ces:alarmRules:get** (Optional)

- **Description**: Get alarm rule details
- **Required for**: Detailed alarm rule inspection
- **API Operation**: `GET /V1.0/{project_id}/alarm-rules/{rule_id}`
- **Use Case**: Debugging alarm rules

### IAM Permissions (Optional)

#### 1. **iam:users:getUser**

- **Description**: Get user information
- **Required for**: Verifying user identity
- **API Operation**: `GET /v3/users/{user_id}`
- **Use Case**: Authentication and authorization checks

#### 2. **iam:users:listUsers** (Optional)

- **Description**: List users
- **Required for**: User management context
- **API Operation**: `GET /v3/users`
- **Use Case**: Multi-user environment context

#### 3. **iam:permissions:listPermissionsForUser** (Optional)

- **Description**: List permissions for user
- **Required for**: Permission verification
- **API Operation**: `GET /v3/users/{user_id}/permissions`
- **Use Case**: Debugging permission issues

## IAM Policy Examples

### 1. Read-Only Policy (Minimum)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ces:metrics:list",
        "ces:metricData:get"
      ],
      "Resource": ["*"],
      "Condition": {
        "StringEquals": {
          "ecs:resource/project_id": ["<your-project-id>"]
        }
      }
    }
  ]
}
```

### 2. Monitoring-Only Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ces:metrics:list",
        "ces:metricData:get",
        "ces:alarms:list",
        "ces:alarms:get",
        "ces:alarmTemplates:list",
        "ces:alarmTemplates:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### 3. Project-Scoped Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ecs:cloudServers:action",
        "ces:metrics:list",
        "ces:metricData:get",
        "ces:alarms:*",
        "ces:alarmTemplates:*",
        "ces:alarmRules:*"
      ],
      "Resource": [
        "ecs:*:*:cloudservers:*",
        "ces:*:*:metrics:*",
        "ces:*:*:alarms:*",
        "ces:*:*:alarm-templates:*",
        "ces:*:*:alarm-rules:*"
      ],
      "Condition": {
        "StringEquals": {
          "ecs:resource/project_id": ["<your-project-id>"],
          "ces:resource/project_id": ["<your-project-id>"]
        }
      }
    }
  ]
}
```

## Creating IAM User and Policy

### Step 1: Create IAM User

1. Log in to Huawei Cloud Console
2. Navigate to **IAM** > **Users**
3. Click **Create User**
4. Enter user details (username, email, etc.)
5. Enable **Programmatic Access**
6. Click **Create**

### Step 2: Create Custom Policy

1. Navigate to **IAM** > **Policies**
2. Click **Create Custom Policy**
3. Enter policy name (e.g., `ECS-Monitoring-ReadOnly`)
4. Select **JSON** as policy syntax
5. Paste the policy JSON from above
6. Click **Create**

### Step 3: Attach Policy to User

1. Navigate to **IAM** > **Users**
2. Select the created user
3. Go to **Permissions** tab
4. Click **Assign Permissions**
5. Select **Attach existing policies**
6. Find and select your custom policy
7. Click **OK**

### Step 4: Create Access Key

1. Navigate to **IAM** > **Users**
2. Select the user
3. Go to **Security Credentials** tab
4. Under **Access Keys**, click **Create Access Key**
5. Download the credentials (CSV file)
6. **Important**: Save the Access Key ID and Secret Access Key securely

## Configuring CLI with IAM Credentials

### Method 1: Interactive Configuration

```bash
hcloud configure init
# Enter:
# - Access Key ID: <from CSV file>
# - Secret Access Key: <from CSV file>
# - Region: <your-region>
# - Project ID: <optional>
# - Output format: json (recommended)
```

### Method 2: Environment Variables

```bash
export HUAWEICLOUD_ACCESS_KEY_ID="your-access-key-id"
export HUAWEICLOUD_SECRET_ACCESS_KEY="your-secret-access-key"
export HUAWEICLOUD_REGION="your-region"
export HUAWEICLOUD_PROJECT_ID="your-project-id"
```

### Method 3: Config File

Edit `~/.hcloud/credentials`:

```ini
[default]
access_key_id = your-access-key-id
secret_access_key = your-secret-access-key
region = your-region
project_id = your-project-id
output = json
```

## Testing Permissions

### Test ECS Access

```bash
# List ECS instances (requires ecs:cloudServers:list)
hcloud ecs list-servers --region <region>

# Get specific instance (requires ecs:cloudServers:get)
hcloud ECS ShowServerDetails <instance-id> --cli-region <region>
```

### Test CES Access

```bash
# List available metrics (requires ces:metrics:list)
hcloud CES ListMetrics --namespace "SYS.ECS" --cli-region <region>

# Get metric data (requires ces:metricData:get)
hcloud CES ShowMetricData \
  --namespace "SYS.ECS" \
  --metric_name "cpu_usage" \
  --dim.0 "instance_id,<instance-id>" \
  --cli-region <region>
```

### Test IAM Access (Optional)

```bash
# Get user info (requires iam:users:getUser)
hcloud iam show-user
```

## Troubleshooting Permission Issues

### 1. "Access Denied" Errors

```bash
# Check current credentials
hcloud configure list

# Test basic IAM access
hcloud iam show-user

# If this fails, credentials may be invalid or expired
```

### 2. "Insufficient Permissions"

```bash
# Verify the exact permission needed
# Check the error message for specific action

# Example error:
# "The user does not have permission to perform action: ecs:cloudServers:list"

# Solution: Add the missing permission to IAM policy
```

### 3. "Resource Not Found"

```bash
# Check if resource exists
hcloud ecs list-servers --region <region>

# Verify resource ID
# Check project ID in policy conditions
```

### 4. "Invalid Region"

```bash
# List available regions
hcloud ecs list-regions

# Verify region format
# Common regions: cn-north-1, cn-east-2, ap-southeast-1
```

## Security Best Practices

### 1. Principle of Least Privilege

- Grant only necessary permissions
- Start with read-only access
- Add write permissions only when required

### 2. Regular Access Key Rotation

- Rotate access keys every 90 days
- Use IAM policy to enforce key expiration
- Monitor key usage in Cloud Trace Service

### 3. Monitor and Audit

- Enable Cloud Trace Service
- Review access logs regularly
- Set up alerts for suspicious activities

### 4. Use IAM Conditions

- Restrict by IP address range
- Limit by time of day
- Require MFA for sensitive operations

### 5. Separate Accounts

- Use different accounts for different purposes
- Separate production and development access
- Use service accounts for automated tasks

## References

- [Huawei Cloud IAM Documentation](https://support.huaweicloud.com/intl/en-us/usermanual-iam/iam_01_0001.html)
- [IAM Policy Syntax](https://support.huaweicloud.com/intl/en-us/usermanual-iam/iam_01_0017.html)