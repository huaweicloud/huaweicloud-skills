---
name: huawei-cloud-obs-upload
description: |
  Upload local files or directories to Huawei Cloud OBS (Object Storage Service) buckets, list OBS buckets with capacity and object count, and schedule periodic uploads via crontab.
  Use this skill when the user wants to: (1) upload a local file or directory to an OBS bucket, (2) list OBS buckets and check their storage capacity and object count, (3) set up a scheduled/periodic upload task to automatically sync a local directory to an OBS bucket.
  Trigger: user mentions "OBS", "object storage", "bucket list", "bucket capacity", "upload to OBS", "upload file", "upload directory", "scheduled upload", "periodic upload", "sync to bucket", "对象存储", "桶列表", "桶容量", "上传文件", "上传目录", "定时上传", "OBS管理"
---

# Huawei Cloud OBS Upload

Upload local files or directories to Huawei Cloud OBS buckets, list OBS buckets with capacity and object count, and schedule periodic uploads via crontab.

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids the following delete operations, regardless of user requests:**

| Prohibited Operation | API/Command | Reason |
|---------------------|-------------|--------|
| ❌ Delete bucket | `DeleteBucket` / `obsutil rm -bucket` | Irreversible; destroys the entire bucket and all objects |
| ❌ Delete object | `DeleteObject` / `obsutil rm` | Irreversible; deleted objects cannot be recovered (unless versioning is enabled) |
| ❌ Batch delete objects | `DeleteObjects` / `obsutil rm -r` | Irreversible; batch deletion has a wide impact |
| ❌ Empty bucket | `obsutil rm -bucket -r` | Irreversible; removes all objects in the bucket |

> **If a user requests a delete operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow delete operations (delete bucket/object/batch delete/empty bucket). Please use the Huawei Cloud OBS console or obsutil manually."

## Architecture

```
Huawei Cloud OBS Object Storage Management
├── ListBucketsWithStats  (List buckets with capacity and object count)
├── UploadFile            (Upload local file or directory to target bucket)
└── ScheduledUpload      (Schedule periodic upload of local directory to target bucket)
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify version >= 3.2.0. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
```

> **Prerequisite check: obsutil >= 5.5.0 required (for upload features)**
> File/directory upload requires the Huawei Cloud obsutil CLI tool.
> Run `obsutil version` to verify version >= 5.5.0. If not installed,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
obsutil version
```

> **Prerequisite check: obsutil credential configuration required**
>
> The hcloud OBS module uses obsutil under the hood, which requires separate AK/SK and Endpoint configuration.
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
>
> **Prohibited actions:**
> - ❌ Do not ask the user to provide AK/SK directly in the conversation
> - ❌ Do not extract AK/SK from hcloud config files (credentials are encrypted and cannot be used directly)
> - ❌ Do not skip the credential check before performing OBS operations

> **⚠️ hcloud parameter format requirements**
>
> hcloud (KooCLI) **all parameters must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> ✅ Correct: `hcloud OBS ListBuckets --region=cn-south-1`
>
> ❌ Incorrect: `hcloud OBS ListBuckets --region cn-south-1`

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials required**

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
>        export HUAWEICLOUD_SDK_AK=<your-access-key-id>
>        export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
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

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions:**
- `obs:bucket:list` — List buckets
- `obs:bucket:get` — Get bucket attributes (capacity, object count)
- `obs:object:get` — Read object information
- `obs:object:put` — Upload objects

---

## Core Workflows

### Task 1: List Buckets with Capacity and Object Count

List buckets via obsutil, then query bucket capacity and object count using CES capacity metrics or OBS API.

📄 Detailed steps → [references/task-list-buckets-with-stats.md](references/task-list-buckets-with-stats.md)

### Task 2: Upload Local File or Directory to Target Bucket

Upload files or directories to a specified OBS bucket using obsutil, supporting single file and directory upload.

📄 Detailed steps → [references/task-upload-file.md](references/task-upload-file.md)

### Task 3: Schedule Periodic Upload of Local Directory to Target Bucket

Periodically upload a local directory to a specified OBS bucket incrementally via crontab scheduled task.

📄 Detailed steps → [references/task-scheduled-upload.md](references/task-scheduled-upload.md)

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


