---
name: huawei-cloud-obs-bucket-create
description: |
  Skill specialized for creating buckets on Huawei Cloud OBS. Use this skill when users need to create OBS buckets, set bucket properties, configure access permissions, or need guidance on the bucket creation process. Triggers include: "创建OBS桶", "华为云存储桶", "存储空间创建", "create OBS bucket", "Huawei Cloud storage bucket", "OBS bucket", "Huawei Cloud bucket", "storage creation" or when setting up Huawei Cloud object storage.
tags: [huawei-cloud, obs, storage, bucket]
---

# Huawei Cloud OBS Bucket Create Skill

## Overview

This skill is used for creating buckets on Huawei Cloud Object Storage Service (OBS). It provides a simple, interactive bucket creation process, including bucket name validation, region selection, access permission configuration, and other advanced options.

**Applicable Scenarios**:

- Creating new buckets on Huawei Cloud OBS
- Setting bucket access permissions and policies
- Configuring bucket region and storage class
- Validating bucket names against specifications
- Batch creation of multiple buckets

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Unsupported Operations

This skill is **only** for creating OBS buckets, listing buckets and checking bucket properties. It does **NOT** execute the following operations. When the user requests any of them, clearly refuse and suggest the alternative command:

| Unsupported Operation | Alternative Command |
|-----------------------|---------------------|
| Delete bucket / object | `hcloud OBS rm` |
| Upload / download files | `hcloud OBS cp` |
| Lifecycle rule management | `hcloud OBS lifecycle` |
| Change bucket attributes | `hcloud OBS chattri` |

> **Refusal guidance**: when a request falls into the table above (or is any operation other than bucket creation/list/stat), tell the user "The skill does not support this operation" and provide the matching `hcloud OBS` alternative command shown above. Do not attempt to run unsupported operations.

## Prerequisites

### 1. Huawei Cloud CLI Tool Installed

Required check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0

  ```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- ` — bare `hcloud` calls are strictly forbidden.**

# Check if installed
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud version
```

If not installed, or version is lower than 3.2.0, refer to [cli-installation-guide.md](references/cli-installation-guide.md) for KooCLI installation.
KooCLI has built-in obsutil tool, if KooCLI version check passes, obsutil check can be skipped.

### 2. Huawei Cloud Credentials Configured

- Valid Huawei Cloud OBS credentials (AK/SK mode)

```bash
# View configuration
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud obs ls -s

# Configuration file location ~/.obsutilconfig
```

If Huawei Cloud credentials are not configured, prompt the user to execute the following command:

```bash
# Configure Huawei Cloud credentials
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS config -i="<Your AK>" -k="<Your SK>" -e="obs.<Region>.myhuaweicloud.com"
```

>**Huawei Cloud OBS credentials do not inherit from Huawei Cloud credentials and need to be set separately.**

- **Security Rules**:
  - 🚫 Do not directly enter AK/SK values in plain text.
  - 🚫 Never expose AK/SK values, do not extract AK/SK from hcloud configuration files.
  - ✅ Only use `hcloud configure list` to check credential status.
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`
## Core Workflow

Bucket name `bucket-name` is a required condition for creating an OBS bucket. If the context does not specify a bucket name, prompt the user that a specific bucket name is needed, no other text prompts required.

### Step 1: Validate Bucket Name

Bucket name rules are as follows:
  > 1. 3-63 characters, starting with a number or letter, supporting lowercase letters, numbers, "-", ".".
  > 2. IP address format is not allowed.
  > 3. Cannot start or end with "-" or ".".
  > 4. Two adjacent "." are not allowed (e.g., "my..bucket").
  > 5. Adjacent "." and "-" are not allowed (e.g., "my-.bucket" and "my.-bucket")."

>If the bucket name does not comply with the specification. Remind the user to reset the bucket name.

### Step 2: Select Region

Get the region for the OBS bucket to be created from the context.

> **IMPORTANT**: `-location` must **always be explicitly specified**. Do NOT rely on the `endpoint` value in `~/.obsutilconfig` as a default region — creating a bucket without an explicit `-location` fails with `IllegalLocationConstraintException`. If the context does not specify a region, prompt the user to provide one (e.g. `cn-north-4`).

**Region validation**: before creating the bucket, validate the region chosen by the user against the valid region list below. If the region is invalid, do NOT run the create command; instead return a friendly message:

> The region `{region}` is invalid. Please use a valid region, e.g. `cn-north-4`, `cn-east-2`, `cn-south-1`, `ap-southeast-1`, etc.

Valid OBS regions (also see <https://developer.huaweicloud.com/intl/en-us/endpoint>):

| Region Code | Region | Region Code | Region |
|-------------|--------|-------------|--------|
| cn-north-1 | North China-Beijing 1 | cn-north-4 | North China-Beijing 4 |
| cn-north-9 | North China-Ulanqab 1 | cn-north-5 | North China-Hohhot 2 |
| cn-east-2 | East China-Shanghai 2 | cn-east-3 | East China-Shanghai 1 |
| cn-east-4 | East China-Shanghai 4 | cn-east-5 | East China-Nanjing 1 |
| cn-south-1 | South China-Guangzhou | cn-south-2 | South China-Shenzhen |
| cn-south-4 | South China-Guangzhou 2 | cn-south-5 | South China-Guangzhou 3 |
| cn-south-21 | South China-Guangzhou 4 | cn-southwest-2 | Southwest-Guiyang 1 |
| cn-southeast-1 | East China-Fuzhou 1 | ap-southeast-1 | Asia Pacific-Hong Kong |
| ap-southeast-2 | Asia Pacific-Bangkok | ap-southeast-3 | Asia Pacific-Singapore |
| ap-southeast-4 | Asia Pacific-Jakarta | ap-southeast-5 | Asia Pacific-Hyderabad |
| ap-southeast-6 | Asia Pacific-Tokyo 1 | ap-southeast-7 | Asia Pacific-Mumbai |
| ap-northeast-1 | Asia Pacific-Tokyo | af-south-1 | Africa-Johannesburg |
| la-south-2 | Latin America-Santiago | na-mexico-1 | Latin America-Mexico City 1 |
| sa-brazil-1 | Latin America-Sao Paulo 1 | eu-west-101 | Europe-Paris 2 |
| eu-west-0 | Europe-Paris 1 | | |

Return prompt text:
>Once a bucket is created successfully, the region cannot be changed, please choose carefully. The region you want to create the bucket in is ${region}

### Step 3: Create Bucket

```bash
# Create with recommended configuration (-location is required)
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS mb obs://bucket-name -location=cn-north-4 [-acl=xxx] [-fs] [-az=xxx] [-sc=xxx] [-epid=xxx] [-kms=xxx]
```

```bash
# Batch create multiple buckets with auto-generated names (prefix-purpose-timestamp).
# Script exit code 6 from Huawei Cloud CLI is normal behavior, not an execution error
./scripts/batch_create_buckets.sh <bucket-name-prefix> <regions> <purpose1> [purpose2] ...
```

```bash
# Batch create multiple buckets with user-specified names (comma-separated)
./scripts/batch_create_buckets.sh --names "bucket-a,bucket-b,bucket-c" --region <region>
```

### Step 4: Validate Success (Optional)


```bash
# List all buckets to confirm creation success
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS ls

# Check bucket properties
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS stat obs://bucket-name
```
If the bucket list contains the bucket name created this time and the bucket information is output normally, prompt that the creation is successful and list the basic information of the bucket.


## Core Commands

### Create Storage Bucket

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS mb obs://bucket-name -location=cn-north-4 [-acl=xxx] [-az=xxx] [-sc=xxx] [-epid=xxx] [-kms=xxx] [-fs]
```

> **Note**: `-location` is required. Always pass an explicit `-location=<region>` from the valid region list in [Step 2](#step-2-select-region); creating a bucket without it fails with `IllegalLocationConstraintException`.

| Option | Description | Possible Values |
|--------|-------------|-----------------|
| `-location=xxx` | Region (required) | cn-north-4, cn-east-2, cn-south-1, ap-southeast-1, etc. |
| `-acl=xxx` | Access Control List | private, public-read, public-read-write |
| `-az=xxx` | Availability Zone | multi-az |
| `-sc=xxx` | Default Storage Class | standard, warm, cold, deep-archive |
| `-epid=xxx` | Enterprise Project ID | Obtained from the Enterprise Project Management (EPS) console or API |
| `-kms=xxx` | KMS Key ID for SSE-KMS encryption | Obtained from the Data Encryption Workshop (DEW/KMS) console; key must exist in the same region |
| `-fs` | Create as a file-optimized (parallel file system) bucket | — |

### List Storage Buckets

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS ls
```

### View Storage Bucket Properties

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-bucket-create -- hcloud OBS stat obs://${bucket-name}
```


## Parameter Confirmation

### Required Parameters

- **bucket-name**: Storage bucket name, must comply with OBS naming convention (3-63 characters, lowercase letters, numbers, hyphens, dots, not starting or ending with hyphen or dot)

### Optional Parameters

- **region**: Region code, such as cn-north-4 (North China-Beijing 4), cn-east-2 (East China-Shanghai 2), cn-south-1 (South China-Guangzhou). **Must be one of the valid regions listed in [Step 2](#step-2-select-region) and should be explicitly passed via `-location`.** Use the region closest to users to reduce latency.
- **acl**: Access permission, default private
- **storage-class**: Storage class, default standard
- **az**: Availability zone, default single availability zone, can be set to multi-az (multi-availability zone)
- **epid**: Enterprise Project ID, used to assign the bucket to a specific enterprise project. Leave empty to use the default project.
- **kms**: KMS Key ID, used to enable SSE-KMS encryption on the created bucket. The key must exist in the same region as the bucket.


## Best Practices

1. **Naming Convention**: Use meaningful bucket names, such as `project-name-environment-purpose-20250527`
2. **Region Selection**: Choose the region closest to users to reduce latency, Beijing 4 (cn-north-4) is a commonly used region
3. **Access Control**: Use private ACL by default, only open public-read when needed
4. **Storage Class**: Choose based on access frequency:
   - Standard storage (standard): Frequently accessed data
   - Infrequent access storage (warm): Infrequently accessed data
   - Archive storage (cold): Rarely accessed data
   - Deep archive storage (deep-archive): Very rarely accessed data
5. **Batch Creation**: Use `batch_create_buckets.sh` script to batch create multiple buckets
6. **Version Control**: Consider enabling bucket version control to prevent accidental deletion

## Notes

1. **Bucket Name Uniqueness**: Bucket name is globally unique in Huawei Cloud OBS, cannot be duplicated with other users
2. **Region Immutability**: Cannot change the bucket region after creation
3. **Cost**: Storage buckets are free, but storing data, requests, and traffic will incur costs
4. **Security**: Do not hard-code AK/SK in scripts, use environment variables or configuration files
5. **Permissions**: Ensure the user executing the command has sufficient OBS permissions
6. **Network**: Ensure network can access Huawei Cloud OBS service endpoints
7. **Quota**: Check account's OBS bucket quantity quota
8. **Deletion Protection**: Important buckets can enable deletion protection to prevent accidental deletion

## References

| Document | Description |
|----------|-------------|
| [KooCLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation guide |
| [Common Errors and Solutions](references/trouble-shooting.md) | Error troubleshooting |
