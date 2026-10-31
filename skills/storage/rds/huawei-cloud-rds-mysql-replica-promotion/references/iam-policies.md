# IAM Authentication Guide

## Overview

The Huawei Cloud RDS single-to-HA skill uses the `hcloud` CLI to call Huawei Cloud APIs
(RDS instance query, flavor query, backup policy, manual backup, single-to-HA action, job
polling, plus IAM and ECS for project/AZ discovery). Authentication is handled through IAM
(Identity and Access Management) credentials and is shared by all scripts in this project
through the hcloud profile.

## Authentication Methods

### Method 1: AK/SK (Recommended)

Use Access Key ID and Secret Access Key — the most common approach for CLI and programmatic
access.

**Configure via hcloud CLI:**

```bash
hcloud configure set \
  --cli-access-key=YOUR_AK \
  --cli-secret-key=YOUR_SK \
  --cli-region=cn-north-4
```

**Or via environment variables:**

```bash
export HWCloudAccessKeyID=YOUR_AK
export HWCloudSecretAccessKey=YOUR_SK
export HWCloudRegion=cn-north-4
```

### Method 2: Token-based

> **Conceptual note only.** A temporary token can be obtained from IAM for scenarios where
> AK/SK is not available. Passing a password directly on the command line is a security
> anti-pattern (it can leak via the process list); this skill's scripts do **not** use this
> authentication path. The recommended approach is always AK/SK + environment variables
> (see Method 1 above).

## Auto-detecting the Project ID

The scripts resolve the region's `project_id` automatically — no `--project-id` parameter
is needed:

```bash
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-4
```

The response's `projects[]` entries carry `id`, `name` (region name) and `domain_id`; the
scripts match `projects[].name == <region>` to resolve the project ID. Key facts
(verified remotely):

- project_id is region-scoped; different regions of the same account have different
  project_ids, while `domain_id` is globally consistent.
- The resolved project_id is recorded in the report `metadata` for traceability.

## Availability Zone Discovery

Availability zones are listed through the ECS service (RDS has no standalone AZ API):

```bash
hcloud ECS NovaListAvailabilityZones --cli-region=cn-north-4 --project_id=<project_id>
```

The response's `availabilityZoneInfo[]` carries `zoneName` and `zoneState.available`.
A zone with `available: false` is not selectable, and the target AZ for the standby node
must differ from the master node's current AZ.

## Required Permissions

The account must have the following permissions to run the conversion workflow:

| Permission | API | Purpose |
|------------|-----|---------|
| `rds:instance:list` | RDS ListInstances | Query instances and verify instance type/status |
| `rds:flavor:list` | RDS ListFlavors | Verify HA flavor support and target AZ availability |
| `rds:backup:list` | RDS ShowBackupPolicy / ListBackups | Verify backup policy; poll backup status |
| `rds:backup:create` | RDS CreateManualBackup | Create the pre-conversion manual backup |
| `rds:instance:singleToHa` | RDS StartInstanceSingleToHaAction | Execute the single-to-HA conversion |
| `rds:job:list` | RDS ListJobInfo | Poll the conversion job status |
| `iam:projects:list` | IAM KeystoneListAuthProjects | Resolve the region's project_id |
| `ecs:availabilityZone:list` | ECS NovaListAvailabilityZones | List availability zones |

## Region Configuration

Specify the region when running each script (every script requires `--region`, with no
default value):

```bash
python3 scripts/list_instances.py --region cn-north-4
python3 scripts/list_azs.py --region cn-north-4
python3 scripts/pre_check.py --region cn-north-4 --instance-id <iid> --target-az cn-north-4b
python3 scripts/convert.py --region cn-north-4 --instance-id <iid> --target-az cn-north-4b
python3 scripts/resume.py --region cn-north-4 --instance-id <iid> [--target-az cn-north-4b]
```

Common regions:

- `cn-north-4` — Beijing 4
- `cn-north-1` — Beijing 1
- `cn-east-3` — Shanghai 1
- `cn-south-1` — Guangzhou

## Security Notes

- **Never** hardcode AK/SK in scripts or configuration files committed to version control.
- Use environment variables or the hcloud profile (stored locally with restricted
  permissions).
- Rotate AK/SK periodically following your organization's security policy.
- The skill scripts do not store or log credentials; all authentication is delegated to the
  `hcloud` CLI.
