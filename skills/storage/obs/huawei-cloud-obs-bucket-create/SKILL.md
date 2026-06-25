---
name: huawei-cloud-obs-bucket-create
description: |
  Skill specialized for creating buckets on Huawei Cloud OBS. Use this skill when users need to create OBS buckets, set bucket properties, configure access permissions, or need guidance on the bucket creation process. Trigger conditions: "创建OBS桶", "华为云存储桶", "存储空间创建", "create OBS bucket", "Huawei Cloud storage bucket", "OBS bucket", "Huawei Cloud bucket", "storage creation" or when setting up Huawei Cloud object storage.
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

## Prerequisites

### 1. Huawei Cloud CLI Tool Installed

Required check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0

  ```bash
# Check if installed
hcloud version
```

If not installed, or version is lower than 3.2.0, refer to [cli-installation-guide.md](references/cli-installation-guide.md) for KooCLI installation.
KooCLI has built-in obsutil tool, if KooCLI version check passes, obsutil check can be skipped.

### 2. Huawei Cloud Credentials Configured

- Valid Huawei Cloud OBS credentials (AK/SK mode)

```bash
# View configuration
hcloud obs ls -s

# Configuration file location ~/.obsutilconfig
```

If Huawei Cloud credentials are not configured, prompt the user to execute the following command:

```bash
# Configure Huawei Cloud credentials
hcloud OBS config -i="<Your AK>" -k="<Your SK>" -e="obs.<Region>.myhuaweicloud.com"
```

>**Huawei Cloud OBS credentials do not inherit from Huawei Cloud credentials and need to be set separately.**

- **Security Rules**:
  - 🚫 Do not directly enter AK/SK values in plain text.
  - 🚫 Never expose AK/SK values, do not extract AK/SK from hcloud configuration files.
  - ✅ Only use `hcloud configure list` to check credential status.

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

Get the region for the OBS bucket to be created from the context. If no region is specified, use the "endpoint" parameter in the ~/.obsutilconfig file as the region by default.
Return prompt text:
>Once a bucket is created successfully, the region cannot be changed, please choose carefully. The region you want to create the bucket in is ${region}

### Step 3: Create Bucket

```bash
# Create with recommended configuration
hcloud OBS mb obs://bucket-name [-acl=xxx] [-location=xxx] [-fs] [-az=xxx] [-sc=xxx]
```

```bash
# Batch create multiple buckets. Script exit code 6 from Huawei Cloud CLI is normal behavior, not an execution error
./scripts/batch_create_buckets.sh <bucket-name-prefix> <regions>
```

### Step 4: Validate Success (Optional)


```bash
# List all buckets to confirm creation success
hcloud OBS ls

# Check bucket properties
hcloud OBS stat obs://bucket-name
```
If the bucket list contains the bucket name created this time and the bucket information is output normally, prompt that the creation is successful and list the basic information of the bucket.


## Core Commands

### Create Storage Bucket

```bash
hcloud OBS mb obs://bucket-name [-acl=xxx] [-location=xxx] [-fs] [-az=xxx] [-sc=xxx]
```

| Option | Description | Possible Values |
|--------|-------------|-----------------|
| `-acl=xxx` | Access Control List | private, public-read, public-read-write |
| `-location=xxx` | Region | cn-north-4, cn-east-2, etc. |
| `-az=xxx` | Availability Zone | multi-az |
| `-sc=xxx` | Default Storage Class | standard, warm, cold, deep-archive |

### List Storage Buckets

```bash
hcloud OBS ls
```

### View Storage Bucket Properties

```bash
hcloud OBS stat obs://${bucket-name}
```


## Parameter Confirmation

### Required Parameters

- **bucket-name**: Storage bucket name, must comply with OBS naming convention (3-63 characters, lowercase letters, numbers, hyphens, dots, not starting or ending with hyphen or dot)

### Optional Parameters

- **region**: Region code, such as cn-north-4 (North China-Beijing 4), cn-east-2 (East China-Shanghai 2)
- **acl**: Access permission, default private
- **storage-class**: Storage class, default standard
- **az**: Availability zone, default single availability zone, can be set to multi-az (multi-availability zone)


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

## Reference Documentation

| Document | Description |
|----------|-------------|
| [KooCLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation guide |
| [Common Errors and Solutions](references/trouble-shooting.md) | Error troubleshooting |
