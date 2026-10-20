# IAM Policies for Huawei Cloud CES Drill Inspection

## Overview

This document outlines the Identity and Access Management (IAM) policies and permissions
required for the CES Drill Inspection skill. The skill is **read-only** — it queries instance
status and CES monitoring metrics across 19 cloud services, but does not modify any cloud
resources, inject faults, or create alarms.

## Required IAM Permissions Matrix

### Read-Only Permissions — Instance Status Query

| API Action | Permission | Purpose |
|------------|------------|---------|
| `ecs:cloudServers:list` | List ECS instances | Instance status collection |
| `ecs:cloudServers:get` | Get ECS instance details | Instance status collection |
| `rds:instances:list` | List RDS instances | Instance status collection |
| `rds:instances:get` | Get RDS instance details | Primary/standby role check |
| `dcs:instances:list` | List DCS instances | Instance status collection |
| `elb:loadbalancers:list` | List ELB instances | Instance status collection |
| `eip:publicIps:list` | List EIPs | Instance status collection |
| `nat:natGateways:list` | List NAT gateways | Instance status collection |
| `vpc:vpceps:list` | List VPC endpoints | Instance status collection |
| `evs:volumes:list` | List EVS volumes | Instance status collection |
| `cce:clusters:list` | List CCE clusters | Instance status collection |
| `css:clusters:list` | List CSS clusters | Instance status collection |
| `dds:instances:list` | List DDS instances | Instance status collection |
| `dws:clusters:list` | List DWS clusters | Instance status collection |
| `dc:directConnects:list` | List Direct Connects | Instance status collection |
| `er:instances:list` | List ER instances | Instance status collection |
| `sfs:turboShares:list` | List SFS Turbo shares | Instance status collection |
| `apig:instances:list` | List APIG instances | Instance status collection |
| `gaussdb:instances:list` | List GaussDB instances | TaurusDB/GeminiDB status |
| `dms:instances:list` | List DMS instances | Kafka/RabbitMQ/RocketMQ status |

### Read-Only Permissions — CES Metric Data Query

| API Action | Permission | Purpose |
|------------|------------|---------|
| `ces:metrics:list` | List available metrics | Discover monitorable metrics |
| `ces:metricData:get` | Get metric data | Query monitoring data across drill phases |

## Minimum Required Permissions

The skill requires only read-only permissions. No write or admin permissions are needed.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "rds:instances:list",
        "rds:instances:get",
        "dcs:instances:list",
        "elb:loadbalancers:list",
        "eip:publicIps:list",
        "nat:natGateways:list",
        "vpc:vpceps:list",
        "evs:volumes:list",
        "cce:clusters:list",
        "css:clusters:list",
        "dds:instances:list",
        "dws:clusters:list",
        "dc:directConnects:list",
        "er:instances:list",
        "sfs:turboShares:list",
        "apig:instances:list",
        "gaussdb:instances:list",
        "dms:instances:list",
        "ces:metrics:list",
        "ces:metricData:get"
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

## Permission Details by Service

### ECS (Elastic Cloud Server)

| Permission | Description | API Operation |
|------------|-------------|---------------|
| `ecs:cloudServers:list` | List ECS instances | `GET /v1/{project_id}/cloudservers` |
| `ecs:cloudServers:get` | Get ECS instance details | `GET /v1/{project_id}/cloudservers/{server_id}` |

### RDS (Relational Database Service)

| Permission | Description | API Operation |
|------------|-------------|---------------|
| `rds:instances:list` | List RDS instances | `GET /v3/{project_id}/instances` |
| `rds:instances:get` | Get RDS instance details (primary/standby role) | `GET /v3/{project_id}/instances/{id}` |

### DCS (Distributed Cache Service)

| Permission | Description | API Operation |
|------------|-------------|---------------|
| `dcs:instances:list` | List DCS instances | `GET /v2/{project_id}/instances` |

### CES (Cloud Eye Service)

| Permission | Description | API Operation |
|------------|-------------|---------------|
| `ces:metrics:list` | List available metrics | `GET /V1.0/{project_id}/metrics` |
| `ces:metricData:get` | Get metric data | `POST /V1.0/{project_id}/metric-data` |

### Other Services (ELB, EIP, NAT, VPCEP, EVS, CCE, CSS, DDS, DWS, DC, ER, SFS, APIG, GaussDB, DMS)

Each service requires only its `list` (and `get` where applicable) read-only permission for
instance status collection. See the minimum required permissions JSON above for the complete list.

## IAM Policy Examples

### 1. Read-Only Policy (Minimum, All Services)

This is the minimum required permissions for the skill to function. See the JSON block above.

### 2. Project-Scoped Policy

For production environments where project-level isolation is needed:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "rds:instances:list",
        "rds:instances:get",
        "dcs:instances:list",
        "ces:metrics:list",
        "ces:metricData:get"
      ],
      "Resource": ["*"],
      "Condition": {
        "StringEquals": {
          "g:ProjectId": ["<your-project-id>"]
        }
      }
    }
  ]
}
```

### 3. ECS-Only Inspection Policy

If only inspecting ECS instances (reduced permission set):

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
3. Enter policy name (e.g., `CES-DrillInspection-ReadOnly`)
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
hcloud ECS NovaListServers --cli-region <region-id>
```

### Test RDS Access

```bash
# List RDS instances (requires rds:instances:list)
hcloud RDS ListInstances --cli-region <region-id>
```

### Test CES Access

```bash
# List available metrics (requires ces:metrics:list)
hcloud CES ListMetrics --namespace "SYS.ECS" --cli-region <region-id>

# Get metric data (requires ces:metricData:get)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region <region-id>
```

## Troubleshooting Permission Issues

### 1. "Access Denied" Errors

```bash
# Check current credentials
hcloud configure list

# Test basic access
hcloud IAM ShowUser
```

### 2. "Insufficient Permissions"

```bash
# Verify the exact permission needed
# Check the error message for specific action
# Example: "The user does not have permission to perform action: rds:instances:list"
# Solution: Add the missing permission to IAM policy
```

### 3. "Resource Not Found"

```bash
# Check if resource exists in the specified region
# Verify project ID in policy conditions
```

### 4. "Invalid Region"

```bash
# Verify region format
# Common regions: cn-north-1, cn-north-4, cn-east-2, ap-southeast-1
# Ensure the region matches where the resource was created
```

## Security Best Practices

### 1. Principle of Least Privilege
- Grant only the read-only permissions listed above
- This skill never needs write or admin permissions
- Use project-scoped policies in production

### 2. Regular Access Key Rotation
- Rotate access keys every 90 days
- Monitor key usage in Cloud Trace Service

### 3. Separate Accounts
- Use a dedicated inspection account
- Separate production and development access

## References

- [Huawei Cloud IAM Documentation](https://support.huaweicloud.com/intl/en-us/usermanual-iam/iam_01_0001.html)
- [IAM Policy Syntax](https://support.huaweicloud.com/intl/en-us/usermanual-iam/iam_01_0017.html)
