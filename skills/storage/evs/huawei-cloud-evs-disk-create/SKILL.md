---
name: huawei-cloud-evs-disk-create
description: |
  Skill specialized for creating EVS disks on Huawei Cloud. Use this skill when users need to create cloud disks (EVS), set disk types, configure disk size, select availability zones, or need guidance on the disk creation process. Trigger conditions: "创建云硬盘", "华为云EVS", "创建磁盘", "创建云盘", "create EVS disk", "Huawei Cloud disk", "EVS disk", "cloud disk", "volume create", "云硬盘创建" or when setting up Huawei Cloud block storage.
tags: [huawei-cloud, evs, storage, disk, volume]
---

# Huawei Cloud EVS Disk Create Skill

## Overview

This skill is used for creating EVS disks on Huawei Cloud Elastic Volume Service (EVS). It provides a simple, interactive disk creation process, including disk type selection, size configuration, availability zone selection, and other advanced options.

**Applicable Scenarios**:

- Creating new EVS disks on Huawei Cloud
- Setting disk types (SSD, GPSSD, SAS, SATA, ESSD, GPSSD2, ESSD2)
- Configuring disk size and availability zone
- Creating disks from snapshots
- Batch creation of multiple disks

## Prerequisites

### 1. Huawei Cloud CLI Tool Installed

Required check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0

  ```bash
  # Check if installed
  hcloud version
  ```

If not installed, or version is lower than 3.2.0, refer to [cli-installation-guide.md](references/cli-installation-guide.md) for KooCLI installation.

### 2. Huawei Cloud Credentials Configured

- Valid Huawei Cloud credentials (AK/SK mode)

```bash
# View configuration
hcloud configure list
```

If Huawei Cloud credentials are not configured, prompt the user to execute the following command:

```bash
# Configure Huawei Cloud credentials (interactive mode)
hcloud configure init
```

>**Security Rules**:
>  - 🚫 Do not directly enter AK/SK values in plain text.
>  - 🚫 Never expose AK/SK values, do not extract AK/SK from hcloud configuration files.
>  - ✅ Only use `hcloud configure list` to check credential status.

> **⚠️ hcloud parameter format requirements**
>
> hcloud (KooCLI) **all parameters must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> ✅ Correct: `hcloud EVS CreateVolume --cli-region=cn-north-4 --volume.name=my-disk`
>
> ❌ Incorrect: `hcloud EVS CreateVolume --cli-region cn-north-4 --volume.name my-disk`
>
> **CreateVolume request body parameters must use the `--volume.` prefix**:
>
> ✅ Correct: `--volume.name=my-disk --volume.size=40 --volume.volume_type=GPSSD --volume.availability_zone=cn-north-4a`
>
> ❌ Incorrect: `--name=my-disk --size=40 --volume_type=GPSSD --availability_zone=cn-north-4a`

## Core Workflow

Disk name `disk-name` and availability zone `availability-zone` are required conditions for creating an EVS disk. If the context does not specify a disk name or availability zone, prompt the user that these parameters are needed.

### Step 1: Select Disk Type

EVS disk types are as follows:

| Disk Type | Specification Code | Max IOPS | Max Throughput | Applicable Scenario |
|-----------|-------------------|----------|---------------|-------------------|
| Ultra-high I/O (ESSD) | SSD | 128,000 | 1,000 MB/s | High-performance databases, key business |
| General-purpose SSD Plus (GPSSD2) | GPSSD2 | 128,000 | 1,000 MB/s | Medium and large databases, business systems |
| Ultra-high I/O (ESSD2) | ESSD2 | 256,000 | 4,000 MB/s | Ultra-high performance databases, AI |
| General-purpose SSD (GPSSD) | GPSSD | 20,000 | 320 MB/s | General business, development and testing |
| High I/O (SAS) | SAS | 8,000 | 250 MB/s | General applications, medium workloads |
| Common I/O (SATA) | SATA | 1,500 | 100 MB/s | Infrequent access, cold data |

> If the user does not specify a disk type, use GPSSD (General-purpose SSD) by default.

### Step 2: Configure Disk Size

Disk size rules are as follows:

| Disk Type | Min Size (GB) | Max Size (GB) | Step Size (GB) |
|-----------|--------------|---------------|---------------|
| SSD | 10 | 32,768 | 1 |
| GPSSD2 | 10 | 32,768 | 1 |
| ESSD2 | 10 | 32,768 | 1 |
| GPSSD | 10 | 32,768 | 1 |
| SAS | 10 | 32,768 | 1 |
| SATA | 10 | 32,768 | 1 |

> If the user does not specify disk size, use 40 GB by default.

### Step 3: Select Availability Zone

Get the availability zone for the EVS disk to be created from the context. If no availability zone is specified, prompt the user to select one.

```bash
# Query available availability zones
hcloud EVS CinderListAvailabilityZones --cli-region=<region>
```

> Once a disk is created successfully, the availability zone cannot be changed, please choose carefully.

### Step 4: Create Disk

Before executing the disk creation command, confirm with the user all input parameters (disk name, size, disk type, availability zone, region). Only execute after user confirmation.

```bash
# Create with recommended configuration
hcloud EVS CreateVolume --cli-region=<region> --volume.availability_zone=<az> --volume.size=<size> --volume.volume_type=<type> --volume.name=<disk-name>
```

```bash
# Create from snapshot
hcloud EVS CreateVolume --cli-region=<region> --volume.availability_zone=<az> --volume.size=<size> --volume.volume_type=<type> --volume.name=<disk-name> --volume.snapshot_id=<snapshot-id>
```

```bash
# Batch create multiple disks
./scripts/batch_create_disks.sh --prefix <disk-name-prefix> --region <region> --az <az> --count <count>
```

### Step 5: Validate Success (Optional)

```bash
# List all disks to confirm creation success
hcloud EVS ListVolumes --cli-region=<region>

# Check disk details
hcloud EVS ShowVolume --cli-region=<region> --volume_id=<volume-id>
```

If the disk list contains the disk name created this time and the disk status is "available", prompt that the creation is successful and list the basic information of the disk.

## Core Commands

### Create EVS Disk

```bash
hcloud EVS CreateVolume --cli-region=<region> --volume.availability_zone=<az> --volume.size=<size> --volume.volume_type=<type> --volume.name=<disk-name> [--volume.snapshot_id=<snapshot-id>] [--volume.description=<desc>] [--volume.enterprise_project_id=<project-id>] [--volume.tags.0.key=<key> --volume.tags.0.value=<value>]
```

| Option | Description | Possible Values |
|--------|-------------|-----------------|
| `--cli-region` | Region | cn-north-4, cn-east-2, etc. |
| `--volume.availability_zone` | Availability Zone | az1, az2, az3, etc. |
| `--volume.size` | Disk Size (GB) | 10-32768 |
| `--volume.volume_type` | Disk Type | SSD, GPSSD2, ESSD2, GPSSD, SAS, SATA |
| `--volume.name` | Disk Name | 1-64 characters |
| `--volume.snapshot_id` | Snapshot ID | UUID format |
| `--volume.description` | Description | 0-255 characters |
| `--volume.enterprise_project_id` | Enterprise Project ID | UUID format |
| `--volume.tags.{*}` | Tags | Key-value pairs |

### List EVS Disks

```bash
hcloud EVS ListVolumes --cli-region=<region>
```

### View EVS Disk Details

```bash
hcloud EVS ShowVolume --cli-region=<region> --volume_id=<volume-id>
```

### Query Available Availability Zones

```bash
hcloud EVS CinderListAvailabilityZones --cli-region=<region>
```

## Parameter Confirmation

### Required Parameters

- **disk-name**: Disk name, must comply with EVS naming convention (1-64 characters, supporting Chinese, English letters, numbers, underscores, hyphens, periods)
- **availability-zone**: Availability zone code, such as cn-north-4a, cn-north-4b
- **region**: Region code, such as cn-north-4 (North China-Beijing 4), cn-east-2 (East China-Shanghai 2)

### Optional Parameters

- **size**: Disk size, default 40 GB
- **volume-type**: Disk type, default GPSSD
- **snapshot-id**: Create from snapshot, optional
- **description**: Disk description, optional
- **enterprise-project-id**: Enterprise project ID, optional
- **tags**: Resource tags, optional

## Best Practices

1. **Type Selection**: Choose disk type based on application I/O requirements:
   - SSD/ESSD: High-performance databases, key business systems
   - GPSSD/GPSSD2: General business, medium workloads
   - SAS: General applications, development and testing
   - SATA: Infrequent access, cold data backup
2. **Availability Zone**: Choose the same availability zone as the ECS instance for optimal performance
3. **Size Planning**: Reserve enough expansion space, disk expansion requires instance restart
4. **Batch Creation**: Use `batch_create_disks.sh` script to batch create multiple disks
5. **Snapshot Creation**: Create from snapshot for quick data recovery and environment replication
6. **Tagging**: Use tags to categorize and manage disk resources

## Notes

1. **Availability Zone Immutability**: Cannot change the disk availability zone after creation
2. **Disk Quota**: Check account's EVS disk quantity quota and total capacity quota
3. **Cost**: Different disk types have different unit prices, SSD is the most expensive, SATA is the cheapest
4. **Security**: Do not hard-code AK/SK in scripts, use environment variables or configuration files
5. **Permissions**: Ensure the user executing the command has sufficient EVS permissions
6. **Network**: Ensure network can access Huawei Cloud EVS service endpoints
7. **Disk Status**: Newly created disk status is "available", needs to be attached to ECS instance before use
8. **Deletion Protection**: Important disks can enable deletion protection to prevent accidental deletion

## Reference Documentation

| Document | Description |
|----------|-------------|
| [KooCLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation guide |
| [IAM Permission Policies](references/iam-policies.md) | Required IAM permissions |
| [Verification Method](references/verification-method.md) | How to verify the skill |
| [Acceptance Criteria](references/acceptance-criteria.md) | Test acceptance criteria |
| [Common Errors and Solutions](references/trouble-shooting.md) | Error troubleshooting |