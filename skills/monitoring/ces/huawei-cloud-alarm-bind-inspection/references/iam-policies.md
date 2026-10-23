# IAM Permissions and Configuration Guide

## Overview
This skill requires read-only IAM permissions to query alarm rules and instance details across Huawei Cloud services. All operations are read-only — no resources are created, modified, or deleted. This document describes the minimum required permissions, AK/SK configuration, and troubleshooting steps.

## Required IAM Permissions Matrix

### CES (Cloud Eye Service) — Alarm Rule Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `ces:alarmRules:list` | List alarm rules | `main_alarm.py` via CES SDK |
| `ces:alarmRules:get` | Get alarm rule details | `main_alarm.py` via CES SDK |

### AOM (Application Operations Management) — Alarm Rule Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `aom:alarmRule:list` | List metric/event alarm rules | `main_aom_alarm.py` via hcloud CLI |

### IAM (Identity and Access Management) — Project ID Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `iam:projects:list` | List projects (KeystoneListProjects) | `config.py` for auto Project ID fetch |

### Instance Detail Query (for metric dimension enrichment)

| Permission | Description | Used By |
|------------|-------------|---------|
| `ecs:servers:get` | Get ECS server details | `enrich_metric_dimension.py` |
| `rds:instances:get` | Get RDS instance details | `enrich_metric_dimension.py` |
| `dcs:instances:get` | Get DCS instance details | `enrich_metric_dimension.py` |
| `elb:loadbalancers:get` | Get ELB load balancer details | `enrich_metric_dimension.py` |
| `vpc:publicIps:get` | Get EIP details | `enrich_metric_dimension.py` |
| Additional service read permissions | For 46 baseline services | `enrich_metric_dimension.py` |

## Minimum Required Permissions

The following custom policy grants the minimum permissions required by this skill:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ces:alarmRules:list",
        "ces:alarmRules:get",
        "aom:alarmRule:list",
        "iam:projects:list"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:get",
        "rds:instances:get",
        "dcs:instances:get",
        "elb:loadbalancers:get",
        "vpc:publicIps:get",
        "dds:instances:get",
        "dms:instances:get",
        "cce:clusters:get",
        "cce:nodes:get",
        "evs:volumes:get",
        "sfs:fileSystems:get",
        "nat:natGateways:get",
        "apig:instances:get",
        "css:clusters:get",
        "dws:clusters:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## AK/SK Configuration

This skill reads credentials from environment variables. Configure them before running:

### Method 1: Environment Variables (Recommended)

```bash
export HW_ACCESS_KEY=your_access_key
export HW_SECRET_KEY=your_secret_key
# Optional: for temporary AK/SK scenarios
export HW_SECURITY_TOKEN=your_security_token
# Optional: skip auto-fetch by providing Project ID directly
export HW_PROJECT_ID=your_project_id
```

### Method 2: .env File

Create a `.env` file in the skill root directory:

```env
HW_ACCESS_KEY=your_access_key
HW_SECRET_KEY=your_secret_key
HW_PROJECT_ID=your_project_id
```

The skill uses `python-dotenv` to automatically load `.env` files.

### Method 3: hcloud CLI Configuration

Configure hcloud interactively (credentials are stored in `~/.hcloud/`):

```bash
hcloud configure init
```

This method is used by `enrich_metric_dimension.py` and `main_aom_alarm.py` which call hcloud CLI internally.

## Creating IAM User and Policy

### Step 1: Create IAM User
1. Log in to Huawei Cloud console → IAM → Users → Create User
2. Select "Programmatic access" (enable AK/SK)
3. Save the generated AK/SK securely

### Step 2: Create Custom Policy
1. IAM → Policies → Create Custom Policy
2. Paste the JSON policy from the "Minimum Required Permissions" section above
3. Name it e.g. `AlarmBindInspectionReadOnly`

### Step 3: Attach Policy to User
1. IAM → Users → select the user → Authorization
2. Select the custom policy `AlarmBindInspectionReadOnly`
3. Confirm

### Step 4: Create Access Key
1. IAM → Users → select the user → Access Keys → Create
2. Save AK/SK securely — SK is only shown once

## Testing Permissions

Verify permissions before running the full workflow:

```bash
# Test CES alarm rule access (via Python SDK)
export HW_ACCESS_KEY=your_ak
export HW_SECRET_KEY=your_sk
python -c "
from scripts.config import get_ces_client
client = get_ces_client('cn-north-4')
print('CES client created successfully')
"

# Test hcloud CLI access
hcloud AOM ListMetricOrEventAlarmRule --cli-region=cn-north-4 --limit=1

# Test IAM project list (for Project ID auto-fetch)
hcloud IAM KeystoneListProjects --cli-region=cn-north-4
```

## Troubleshooting Permission Issues

### 1. "Access Denied" or 403 Errors
- Verify AK/SK are correctly set in environment variables
- Check that the IAM user has the required policy attached
- Ensure the AK/SK has not been disabled or expired

### 2. "Insufficient Permissions"
- Add the specific permission from the matrix above
- For AOM errors, ensure `aom:alarmRule:list` is granted
- For instance enrichment errors, add the corresponding service read permission

### 3. Project ID Auto-fetch Fails
- Ensure `iam:projects:list` permission is granted
- Alternatively, set `HW_PROJECT_ID` environment variable manually
- Check hcloud CLI is installed and configured: `hcloud IAM KeystoneListProjects --cli-region=cn-north-4`

### 4. Multi-region Permission Errors
- IAM permissions are project-scoped; ensure the user has access to all target regions
- Use a cross-project policy or grant permissions in each target project

## Security Best Practices

- **Principle of least privilege**: Only grant the read-only permissions listed above
- **Never commit AK/SK to git**: Use environment variables or `.env` files (add `.env` to `.gitignore`)
- **Regular key rotation**: Rotate AK/SK periodically per your organization's policy
- **Separate accounts**: Use a dedicated IAM user for this skill, not the main account

## References

- IAM Documentation: https://support.huaweicloud.com/usermanual-iam/iam_01_0001.html
- CES Documentation: https://support.huaweicloud.com/api-ces/ces_03_0001.html
- AOM Documentation: https://support.huaweicloud.com/api-aom/aom_04_0001.html
