# IAM Permissions and Configuration Guide

## Overview
This skill requires read-only IAM permissions to query alarm histories and alarm rules across Huawei Cloud CES and AOM services. All operations are read-only — no resources are created, modified, or deleted. This document describes the minimum required permissions, AK/SK configuration, and troubleshooting steps.

## Required IAM Permissions Matrix

### CES (Cloud Eye Service) — Alarm History & Rule Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `ces:alarmHistories:list` | List alarm histories (ListAlarmHistories/v2) | `alarm_api.py` via hcloud CLI |
| `ces:alarmRules:list` | List alarm rules (ListAlarmRules) | `alarm_api.py` via hcloud CLI |

### AOM (Application Operations Management) — Alarm Rule Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `aom:alarmRule:list` | List metric/event alarm rules (ListMetricOrEventAlarmRule) | `alarm_api.py` via hcloud CLI |

### IAM (Identity and Access Management) — Project ID Query

| Permission | Description | Used By |
|------------|-------------|---------|
| `iam:projects:list` | List projects (KeystoneListProjects) | `config.py` for auto Project ID fetch |

### RMS (Resource Management Service) — Instance Discovery

| Permission | Description | Used By |
|------------|-------------|---------|
| `rms:resources:list` | List all resources (ListAllResources) | `generate_instance.py` via hcloud CLI |
| `rms:resourcesSummary:list` | Collect resource summary (CollectAllResourcesSummary) | `generate_instance.py` via hcloud CLI |

## Minimum Required Permissions

The following custom policy grants the minimum permissions required by this skill:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ces:alarmHistories:list",
        "ces:alarmRules:list",
        "aom:alarmRule:list",
        "iam:projects:list",
        "rms:resources:list",
        "rms:resourcesSummary:list"
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
# Optional: default region
export HW_REGION_NAME=cn-south-1
```

### Method 2: .env File (Local Development Only)

Create a `.env` file in the skill root directory (gitignored, not committed):

```env
HW_ACCESS_KEY=your_access_key
HW_SECRET_KEY=your_secret_key
HW_REGION_NAME=cn-south-1
```

The skill uses `python-dotenv` to automatically load `.env` files. The `.env` file is excluded from git via `.gitignore`.

### Method 3: hcloud CLI Configuration

Configure hcloud interactively (credentials are stored in `~/.hcloud/`):

```bash
hcloud configure init
```

This method is used by `alarm_api.py` which calls hcloud CLI internally with `--cli-region` for each region.

## Creating IAM User and Policy

### Step 1: Create IAM User
1. Log in to Huawei Cloud console → IAM → Users → Create User
2. Select "Programmatic access" (enable AK/SK)
3. Save the generated AK/SK securely

### Step 2: Create Custom Policy
1. IAM → Policies → Create Custom Policy
2. Paste the JSON policy from the "Minimum Required Permissions" section above
3. Name it e.g. `AlarmReduceNoiseReadOnly`

### Step 3: Attach Policy to User
1. IAM → Users → select the user → Authorization
2. Select the custom policy `AlarmReduceNoiseReadOnly`
3. Confirm

### Step 4: Create Access Key
1. IAM → Users → select the user → Access Keys → Create
2. Save AK/SK securely — SK is only shown once

## Testing Permissions

Verify permissions before running the full workflow:

```bash
# Test CES alarm history access (via hcloud CLI)
hcloud CES ListAlarmHistories --cli-region=cn-north-4 --limit=1

# Test CES alarm rule access (via hcloud CLI)
hcloud CES ListAlarmRules --cli-region=cn-north-4 --limit=1

# Test AOM alarm rule access (via hcloud CLI)
hcloud AOM ListMetricOrEventAlarmRule --cli-region=cn-north-4 --limit=1

# Test IAM project list (for Project ID auto-fetch)
hcloud IAM KeystoneListProjects --cli-region=cn-north-4

# Test RMS resource summary (for instance discovery)
hcloud RMS CollectAllResourcesSummary --cli-region=cn-north-4

# Test RMS resource list (for instance discovery)
hcloud RMS ListAllResources --cli-region=cn-north-4 --type=ecs.cloudservers --limit=1
```

## Troubleshooting Permission Issues

### 1. "Access Denied" or 403 Errors
- Verify AK/SK are correctly set in environment variables
- Check that the IAM user has the required policy attached
- Ensure the AK/SK has not been disabled or expired

### 2. "Insufficient Permissions"
- Add the specific permission from the matrix above
- For AOM errors, ensure `aom:alarmRule:list` is granted
- For CES alarm history errors, ensure `ces:alarmHistories:list` is granted

### 3. Project ID Auto-fetch Fails
- Ensure `iam:projects:list` permission is granted
- Alternatively, set `HW_PROJECT_ID` environment variable manually
- Check hcloud CLI is installed and configured: `hcloud IAM KeystoneListProjects --cli-region=cn-north-4`

### 4. RMS Instance Discovery Fails (Step 2)
- Ensure `rms:resources:list` and `rms:resourcesSummary:list` permissions are granted
- Verify RMS API access: `hcloud RMS CollectAllResourcesSummary --cli-region=cn-north-4`
- If using a sub-account, RMS permissions may not be available by default — create a custom policy
- RMS is a global service; permissions apply across regions

### 5. Multi-region Permission Errors
- IAM permissions are project-scoped; ensure the user has access to all target regions
- Regions are auto-discovered via RMS API (core_instances.json)
- Use a cross-project policy or grant permissions in each target project

## Security Best Practices

- **Principle of least privilege**: Only grant the read-only permissions listed above
- **Never commit AK/SK to git**: Use environment variables or `.env` files (`.env` is in `.gitignore`)
- **Regular key rotation**: Rotate AK/SK periodically per your organization's policy
- **Separate accounts**: Use a dedicated IAM user for this skill, not the main account

## References

- IAM Documentation: https://support.huaweicloud.com/usermanual-iam/iam_01_0001.html
- CES Documentation: https://support.huaweicloud.com/api-ces/ces_03_0001.html
- AOM Documentation: https://support.huaweicloud.com/api-aom/aom_04_0001.html
- RMS Documentation: https://support.huaweicloud.com/api-rms/rms_02_0001.html
