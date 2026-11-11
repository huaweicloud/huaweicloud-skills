# IAM Authentication Guide

## Overview

The Huawei Cloud RDS single-to-HA skill uses the `hcloud` CLI to call Huawei Cloud APIs
(RDS instance query, flavor query, backup policy, manual backup, single-to-HA action, job
polling, plus IAM for project/domain resolution, RMS for cross-region discovery, BSS for
price quoting and CES for monitoring metrics). Authentication is handled through IAM
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

## Cross-Region Instance Discovery

Instance discovery goes through RMS, which aggregates resources of every region in one
paged call:

```bash
# 1. Resolve the account domain id from the current AK/SK.
hcloud IAM KeystoneListAuthDomains --cli-region=cn-north-4

# 2. Page through every RDS instance of the account.
hcloud RMS ListAllResources --cli-region=cn-north-4 --domain_id=<domain_id> \
  --type=rds.instances --limit=200 [--marker=<next_marker>]
```

Verified facts (2026-11-06):

- RMS **only** accepts `cn-north-4` as its `--cli-region` channel. Any other value fails
  with `cli-region的值不支持,当前支持的区域值如下: cn-north-4`. The instances' real regions
  arrive in each resource's `region_id`.
- `--limit` accepts 1–200; 201 is rejected with `Min.: 1; max.: 200`.
- Pagination uses `--marker` with the previous response's `page_info.next_marker`.
- Single instances report `properties.haMode=Single` and `properties.nodeNum=1`; HA
  instances report `Ha` and `2`. `properties.engineName` is lowercase `mysql`.
- RMS `properties.volumeType` reports `ULTRAHIGH` where ListInstances reports
  `CLOUDSSD`. RMS is for discovery only; storage type, storage size, flavor, version and
  charge mode must be re-read from ListInstances.

## Availability Zone Discovery

Availability is **flavor-scoped**, so zones are read from the HA flavor's `az_status`
instead of a region-wide zone list:

```bash
hcloud RDS ListFlavors --cli-region=<region> --project_id=<project_id> \
  --database_name=MySQL --version_name=8.0 --spec_code=<ha_spec_code>
```

The response's `az_status` maps each zone to `normal` / `sellout` / `unsupported`, and
`az_desc` maps the same zone codes to their display names. Only `normal` is selectable.

The ECS zone list (`hcloud ECS NovaListAvailabilityZones`) is **not** usable for this
decision: it reports a zone as available even when the target RDS flavor is unsupported
there. Verified example (cn-south-1, 2026-11-06): `cn-south-2b` is `available` at the ECS
layer, `normal` for `rds.mysql.x1.xlarge.2`, but `unsupported` for
`rds.mysql.x1.xlarge.2.ha`. The single flavor's `az_status` also differs from its HA
counterpart, so the HA flavor must be queried.

Choosing the same zone as the current one is allowed (shortest intra-zone latency), but it
provides no cross-AZ disaster recovery.

## Required Permissions

The account must have the following permissions to run the conversion workflow:

| Permission | API | Purpose |
|------------|-----|---------|
| `rds:instance:list` | RDS ListInstances | Read authoritative instance detail; verify type/status |
| `rds:flavor:list` | RDS ListFlavors | Verify HA flavor support and target AZ availability |
| `rds:backup:list` | RDS ShowBackupPolicy / ListBackups | Verify backup policy; poll backup status |
| `rds:backup:create` | RDS CreateManualBackup | Create the pre-conversion manual backup |
| `rds:instance:singleToHa` | RDS StartInstanceSingleToHaAction | Execute the single-to-HA conversion |
| `rds:job:list` | RDS ListJobInfo | Poll the conversion job status |
| `iam:projects:list` | IAM KeystoneListAuthProjects | Resolve the region's project_id |
| `iam:domains:list` | IAM KeystoneListAuthDomains | Resolve the account domain_id for RMS |
| `rms:resources:list` | RMS ListAllResources | Discover instances across all regions |
| `bss:discount:list` / rating APIs | BSS ListOnDemandResourceRatings, ListRateOnPeriodDetail | Quote single and HA prices |
| `ces:metric:list` / metric-data read | CES BatchListMetricData, ShowMetricData | Capture the pre-conversion baseline and the post-conversion snapshot |
| `rds:instance:get` | RDS ShowInstanceConfiguration | Read `max_connections` when absolute connection counts are requested |

## Region Configuration

`--region` is always the **instance's** region. The discovery, BSS and conversion channels
are fixed and independent of it:

| Channel | Fixed region | Why |
|---------|--------------|-----|
| RDS / IAM / CES | the instance's region | Region-scoped services |
| RMS | `cn-north-4` | Only accepted value; aggregates all regions |
| BSS | `cn-north-1` | Only accepted value; the real region travels in the quote payload |

```bash
python3 scripts/list_instances.py
python3 scripts/list_azs.py --region cn-north-4 --database-name MySQL \
  --version-name 8.0 --spec-code rds.mysql.n1.large.2.ha --instance-id <iid>
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
