---
name: huawei-cloud-obs-upload
description: |
  Upload local files or directories to Huawei Cloud OBS (Object Storage Service) buckets, list OBS buckets with capacity and object count, and schedule periodic uploads via crontab.
  Use this skill when the user wants to: (1) upload a local file or directory to an OBS bucket, (2) list OBS buckets and check their storage capacity and object count, (3) set up a scheduled/periodic upload task to automatically sync a local directory to an OBS bucket.
  Triggers include: user mentions "OBS", "object storage", "bucket list", "bucket capacity", "upload to OBS", "upload file", "upload directory", "scheduled upload", "periodic upload", "sync to bucket", "对象存储", "桶列表", "桶容量", "上传文件", "上传目录", "定时上传", "OBS管理"
tags: ["obs upload", "obs", "obsutil"]
---

# Huawei Cloud OBS Upload Skill

## Overview

Upload local files or directories to Huawei Cloud OBS buckets, list OBS buckets with capacity and object count, and schedule periodic uploads via crontab. **Upload operations use obsutil; bucket listing/stats use `hcloud obs ls` + CES metrics.**

**Tool separation principle:**
- **obsutil** — File/directory upload, scheduled upload sync (**upload core tool; hcloud CLI has no PutObject support**)
- **hcloud CLI** — Bucket listing via `hcloud obs ls` (obsutil mode), bucket capacity/object count stats via `hcloud CES ShowMetricData`
- **crontab / Task Scheduler** — OS-level scheduled task for periodic upload (no daemon process dependency)

**Security architecture:**
- AK/SK are never read, echoed, or printed in conversation
- obsutil credentials are configured by the user in their terminal (never asked in conversation)
- Delete operations are strictly forbidden (irreversible); out-of-scope operations are refused with guided alternatives
- For directory uploads, whether to preserve directory structure (`-flat`) is decided by the customer's explicit answer, never assumed

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids the following operations, regardless of user requests:**

| Prohibited Operation | Reason |
|---------------------|--------|
| ❌ Delete bucket (`DeleteBucket` / `obsutil rm -bucket`) | Irreversible; destroys the entire bucket and all objects |
| ❌ Delete object (`DeleteObject` / `obsutil rm`) | Irreversible; deleted objects cannot be recovered (unless versioning is enabled) |
| ❌ Batch delete objects (`DeleteObjects` / `obsutil rm -r`) | Irreversible; batch deletion has a wide impact |
| ❌ Empty bucket (`obsutil rm -bucket -r`) | Irreversible; removes all objects in the bucket |
| ❌ Download object (`GetObject` / `obsutil cp obs://... <LocalPath>`) | This skill is upload-only; download is a separate workflow |
| ❌ Create bucket (`CreateBucket` / `obsutil mb`) | Bucket creation has a dedicated skill with full prerequisites |
| ❌ Copy object (`CopyObject` / `hcloud OBS CopyObject`) | Cross-bucket object copy is out of this skill's scope |
| ❌ Lifecycle configuration (`SetBucketLifecycle`) | Storage cost management is a separate bucket-level config task |
| ❌ Restore archived object (`RestoreObject` / `obsutil restore`) | Archive restore is a separate workflow with retrieval modes and TTL |
| ❌ Presigned URL (`CreatePresignedUrl`) | Temporary sharing requires SDK signing; not supported by CLI upload |
| ❌ Bucket ACL/Policy (`SetBucketAcl` / `SetBucketPolicy`) | Permission management is a separate security task |
| ❌ Ask user to provide AK/SK directly in conversation | Credentials must never appear in conversation |
| ❌ Extract AK/SK from hcloud config files | Credentials are encrypted and cannot be used directly |
| ❌ Skip obsutil credential check before OBS operations | Operations fail without configured credentials |
| ❌ Use `-flat` for directory uploads without asking the customer | `-flat` discards directory structure; must follow customer's explicit answer |
| ❌ Guess local path, bucket name, or target prefix | Required parameters must be provided by the user |

> **If a user requests a delete operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow delete operations (delete bucket/object/batch delete/empty bucket). Please use the Huawei Cloud OBS console or obsutil manually."

> **If a user requests an out-of-scope operation, do not attempt to perform it. Inform the user with the recommended alternative from the table below:**

| Operation | Recommended alternative |
|-----------|-------------------------|
| Download object | Use `obsutil cp obs://<Bucket>/<Key> <LocalPath>` manually, or the OBS console |
| Create bucket | Use the dedicated skill [huawei-cloud-obs-bucket-create](https://skills.huaweicloud.com/detail/huawei-cloud-obs-bucket-create), or the OBS console |
| Copy object | Use `hcloud OBS CopyObject` manually, or the OBS console |
| Lifecycle configuration | Use the OBS console (Bucket > Lifecycle), or `hcloud OBS SetBucketLifecycle` |
| Restore archived object | Use `obsutil restore obs://<Bucket>/<Key>` manually, or the OBS console |
| Presigned URL | Use Huawei Cloud SDK (Java/Python/Go) to generate presigned URLs, or the OBS console |
| Bucket ACL/Policy | Use the OBS console (Bucket > Permissions), or `hcloud OBS SetBucketAcl`/`SetBucketPolicy` |

## Architecture

```
Huawei Cloud OBS Upload Management
├── Task 1: ListBucketsWithStats   (List buckets with capacity and object count)
│   ├── 1a. hcloud obs ls: list all buckets
│   ├── 1b. CES metrics / OBS API: query bucket capacity and object count
│   └── 1c. Report bucket stats table to user
├── Task 2: UploadFile             (Upload local file or directory to target bucket)
│   ├── 2a. Confirm local path + bucket name + target prefix with user
│   ├── 2b. For directory: ask customer whether to preserve directory structure (decide -flat)
│   ├── 2c. obsutil cp: single file (-flat) or directory (-r, optional -flat by customer answer)
│   └── 2d. Verify upload result
└── Task 3: ScheduledUpload       (Schedule periodic upload of local directory to target bucket)
    ├── 3a. Confirm local dir + bucket + prefix + schedule period with user
    ├── 3b. Ask customer whether to preserve directory structure (decide -flat)
    ├── 3c. Generate obsutil upload script (with/without -flat per customer answer)
    ├── 3d. Set crontab / Task Scheduler scheduled task
    └── 3e. Verify scheduled task is set
```

## Prerequisites

> **Prerequisite check 1/3: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify version >= 3.2.0. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
```

> **Prerequisite check 2/3: obsutil >= 5.5.0 required (for upload features)**
> File/directory upload requires the Huawei Cloud obsutil CLI tool.
> Run `obsutil version` to verify version >= 5.5.0. If not installed,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
obsutil version
```

> **Prerequisite check 3/3: obsutil credential configuration required**
>
> The hcloud obs module maps to obsutil under the hood, which requires separate AK/SK and Endpoint configuration.
> Before performing OBS operations, **you must check whether obsutil credentials are configured**:
>
> ```bash
> hcloud obs ls -limit=1
> ```
>
> **If the response is `Please set ak, sk and endpoint in the configuration file!` or `InvalidAccessKeyId`, obsutil credentials are not configured.**
>
> **Resolution: Provide the following example command and have the user configure it in their terminal (do not ask the user to provide AK/SK directly in the conversation):**
>
> ```
> obsutil credentials are not configured. Please run the following command in your terminal to configure (AK/SK can be obtained from the Huawei Cloud console "My Credentials" page):
>
>   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<Region>.myhuaweicloud.com
>
> Example (Guangzhou region):
>   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.cn-south-1.myhuaweicloud.com
>
> Common Endpoints:
>   cn-north-4  → obs.cn-north-4.myhuaweicloud.com
>   cn-east-3   → obs.cn-east-3.myhuaweicloud.com
>   cn-south-1  → obs.cn-south-1.myhuaweicloud.com
>   cn-southwest-2 → obs.cn-southwest-2.myhuaweicloud.com
>
> Retry after configuration is complete.
> ```

> **⚠️ hcloud parameter format requirements**
>
> hcloud (KooCLI) cloud-service API commands (uppercase module, e.g. `hcloud CES ShowMetricData`) **must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> ✅ Correct: `hcloud CES ShowMetricData --region=cn-south-1 --namespace=SYS.OBS`
>
> ❌ Incorrect: `hcloud CES ShowMetricData --region cn-south-1`
>
> **Note:** `hcloud obs` (lowercase, obsutil mode) directly maps to obsutil commands and uses obsutil parameter style (e.g. `hcloud obs ls`, `hcloud obs config -i=...`); the `--param=value` rule does not apply. There is no `hcloud OBS ListBuckets` command — use `hcloud obs ls` to list buckets.

---

## Authentication

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing AK/SK values
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
> - **Prohibited** from using `hcloud configure set` to pass plaintext credential values
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or configured CLI config files
>
> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
> 1. **Stop immediately** - Do not execute any commands
> 2. **Politely refuse** and return the following message:
>    ```
>    For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration (recommended)
>        hcloud configure
>        # Enter AK/SK as prompted; credentials will be securely stored in a local config file
>
>    Method 2: Environment variable configuration
>        export HW_ACCESS_KEY=<your-access-key-id>
>        export HW_SECRET_KEY=<your-access-key-secret>
>
>    After configuration is complete, please retry your request.
>    ```
> 3. **Do not continue** executing any Huawei Cloud operations until credentials are configured
>
> **Check CLI configuration**:
> ```bash
>    hcloud configure list
> ```
>    Check whether the output contains valid configuration (AK/SK, IAM, etc.).
>
> **If no valid credentials exist, stop here.**

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for the full permission table.

**Minimum required permissions:**
- `obs:bucket:list` — List buckets
- `obs:bucket:get` — Get bucket attributes (capacity, object count)
- `obs:object:get` — Read object information
- `obs:object:put` — Upload objects

**Permission boundaries:**

- **Scope constraint**: Only upload to and list user-specified buckets. Never delete or modify bucket-level configuration.
- **Must stop if**: credentials missing or invalid, user declines any confirmation, target bucket does not exist, or local path does not exist.
- **Prohibited actions**: any delete operation, any out-of-scope operation listed above, accessing resources outside the user-specified buckets.

---

## Core Workflows

### Task 1: List Buckets with Capacity and Object Count

List buckets via obsutil, then query bucket capacity and object count using CES capacity metrics or OBS API.

> **⚠️ Tool separation: `hcloud obs ls` for listing, `hcloud CES ShowMetricData` for stats**
>
> - **`hcloud obs ls`**: list all buckets (obsutil mode; no `--region` parameter — region is set via `hcloud obs config -e=...`)
> - **`hcloud CES ShowMetricData` / OBS API**: query each bucket's capacity and object count

📄 Detailed steps → [references/task-list-buckets-with-stats.md](references/task-list-buckets-with-stats.md)

**Sub-tasks:**

1. **1a. List buckets** — `hcloud obs ls` (or `obsutil ls`)
2. **1b. Query bucket stats** — CES capacity metrics or OBS API for capacity and object count
3. **1c. Report stats** — Present bucket name, capacity, object count in a table

### Task 2: Upload Local File or Directory to Target Bucket

Upload files or directories to a specified OBS bucket using obsutil, supporting single file and directory upload.

> **⚠️ Upload operations require obsutil, not hcloud**
>
> hcloud CLI does not support OBS object upload operations (no PutObject/UploadPart CLI commands). Uploading files/directories **must use obsutil**.

> **⚠️ For directory uploads, you MUST ask the customer first whether to preserve the source directory structure, then decide whether to use `-flat` based on their explicit answer. Never default.**

📄 Detailed steps → [references/task-upload-file.md](references/task-upload-file.md)

**Sub-tasks:**

1. **2a. Confirm parameters** — local path, target bucket name, target prefix (optional) with the user
2. **2b. Decide `-flat`** — single file: use `-flat` without asking; directory: ask customer whether to preserve directory structure
3. **2c. Execute upload** — `obsutil cp` single file or directory (with/without `-flat` per customer answer)
4. **2d. Verify result** — check upload exit code and confirm object exists in bucket

### Task 3: Schedule Periodic Upload of Local Directory to Target Bucket

Periodically upload a local directory to a specified OBS bucket incrementally via crontab scheduled task.

> **⚠️ Scheduled upload is based on OS-level scheduled task mechanisms (Linux/macOS: crontab, Windows: Task Scheduler), no daemon process dependency.**

> **⚠️ Before generating the scheduled upload script, you MUST ask the customer first whether to preserve the source directory structure, then decide whether to use `-flat` based on their explicit answer. Never default.**

📄 Detailed steps → [references/task-scheduled-upload.md](references/task-scheduled-upload.md)

**Sub-tasks:**

1. **3a. Confirm parameters** — local directory, bucket, prefix, schedule period with the user
2. **3b. Decide `-flat`** — ask customer whether to preserve directory structure
3. **3c. Generate upload script** — `$HOME/obs-scheduled-upload-<BucketName>.sh` (with/without `-flat` per customer answer)
4. **3d. Set scheduled task** — crontab (Linux/macOS) or Task Scheduler (Windows)
5. **3e. Verify** — `crontab -l` or `schtasks /query` to confirm task is set

---

## Core Commands

### obsutil (upload core — hcloud has no PutObject)

```bash
# Upload a single file
obsutil cp <LocalFilePath> obs://<BucketName>/<ObjectKey> -flat

# Upload directory, preserve structure (customer chose "Yes")
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r

# Upload directory, flatten files (customer chose "No")
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat

# Scheduled incremental upload, preserve structure
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -f -u

# Scheduled incremental upload, flatten files
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -f -u

# List buckets
obsutil ls
```

### hcloud CLI (bucket listing + stats)

```bash
# List all buckets (obsutil mode; no --region parameter)
hcloud obs ls

# Check obsutil credential configuration
hcloud obs ls -limit=1

# Configure obsutil credentials (user runs in terminal)
hcloud obs config -i=<AK> -k=<SK> -e=<Endpoint>

# Query bucket capacity/object count stats (cloud-service API mode, --param=value format)
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,my-bucket \
  --period=86400 \
  --filter=average \
  --from=1746057600000 \
  --to=1747612800000
```

> **⚠️ Key constraints on Core Commands:**
>
> - Upload: **MUST use obsutil cp** — hcloud CLI has no PutObject support
> - List buckets: **MUST use `hcloud obs ls`** — there is no `hcloud OBS ListBuckets` command
> - `-flat` for directory uploads: **MUST follow the customer's explicit answer**, never default
> - hcloud cloud-service API params (uppercase module, e.g. `hcloud CES ...`): **MUST use `--param=value` format**; `hcloud obs` (obsutil mode) uses obsutil parameter style
> - AK/SK: **MUST NOT appear in conversation**; user configures obsutil credentials in their terminal

---

## Parameter Confirmation

> **Before executing any task, the following parameters must be confirmed with the user. Guessing is prohibited.**

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Region | Required | Huawei Cloud region (e.g., `cn-south-1`, `cn-north-4`); must be explicitly selected by the user | - |
| Local file/directory path | Required (Task 2/3) | Local path to upload; must exist and be readable | - |
| Target bucket name | Required (Task 2/3) | Target OBS bucket name for upload | - |
| Target path prefix | Optional (Task 2/3) | Target path prefix within the bucket | Bucket root |
| Preserve directory structure | Required (directory upload) | Ask customer: "Yes" → no `-flat`; "No" → `-flat` | - (must ask) |
| Schedule period | Required (Task 3) | Execution period, e.g., hourly, daily at 8:00, every 30 minutes | - |
| Crontab expression | Optional (Task 3) | If user is familiar with cron expressions, they can provide one directly | - |

> **Note**: No AK/SK parameter is required in conversation. Credentials are configured by the user via `hcloud obs config` in their terminal.

---

## Verification Method

See [references/verification-method.md](references/verification-method.md) for details. For common issues and solutions, see [references/troubleshooting.md](references/troubleshooting.md).

**Quick validation:**
```bash
hcloud version && obsutil version && hcloud obs ls -limit=1
```

**Post-upload verification:** `obsutil ls obs://<BucketName>/<Prefix>` to confirm uploaded objects exist.

---

## References

| Document | Description |
|----------|-------------|
| [task-list-buckets-with-stats.md](references/task-list-buckets-with-stats.md) | Task 1: List buckets with capacity and object count |
| [task-upload-file.md](references/task-upload-file.md) | Task 2: Upload file or directory |
| [task-scheduled-upload.md](references/task-scheduled-upload.md) | Task 3: Scheduled upload |
| [related-apis.md](references/related-apis.md) | API and CLI command details |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [obs-metrics.md](references/obs-metrics.md) | OBS CES monitoring metrics reference |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/error pattern comparison |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and practical experience |
