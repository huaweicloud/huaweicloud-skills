---
name: huawei-cloud-obs-stats
description: |
  Query Huawei Cloud OBS (Object Storage Service) statistics: list buckets with capacity and object counts, query extranet/intranet download traffic with month-over-month comparison, and query total requests with month-over-month comparison.
  Use this skill when the user wants to: (1) list OBS buckets and check their storage capacity and object count, (2) query download traffic with MoM comparison, (3) query request counts with MoM comparison.
  Trigger: user mentions "OBS", "object storage", "bucket list", "bucket capacity", "download traffic", "total requests", "request count", "month-over-month", "OBS stats", "OBS management", "对象存储", "桶列表", "桶容量", "下载流量", "请求总数", "月环比", "OBS监控"
tags: ["huawei-cloud", "obs", "stats", "obs metrics"]
---

# Huawei Cloud OBS Statistics Skill

## Overview

Query Huawei Cloud OBS (Object Storage Service) statistics: list buckets with capacity and object counts, query extranet/intranet download traffic with month-over-month comparison, and query total requests with month-over-month comparison.

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
Huawei Cloud OBS Statistics
├── ListBucketsWithStats  (List buckets with capacity and object counts)
├── GetTraffic           (Query extranet/intranet download traffic with MoM comparison)
└── GetRequests           (Query total requests with MoM comparison)
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify version >= 3.2.0. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
```

> **Prerequisite check: obsutil >= 5.5.0 required (for OBS bucket listing)**
> The hcloud OBS module uses obsutil under the hood. Bucket listing requires the obsutil CLI tool.
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

**[Conditional] CLI User-Agent** — `hcloud` OBS module commands may include a User-Agent header, but **the CES module does not support this parameter**:

- ✅ OBS module: `hcloud obs ls`
- ❌ CES module: `hcloud CES ShowMetricData` **does not support** `--User-Agent`; appending it causes "Invalid parameter: User-Agent"

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
- `ces:metric:get` — Query CES monitoring metrics (traffic, request count)

---

## Core Workflows

### Task 1: List Buckets with Capacity and Object Counts

List buckets via obsutil, then query bucket capacity and object count using CES capacity metrics or OBS API.

📄 Detailed steps → [references/task-list-buckets-with-stats.md](references/task-list-buckets-with-stats.md)

### Task 2: Query Extranet/Intranet Download Traffic (with MoM Comparison)

Query download traffic (extranet + intranet) via CES ShowMetricData, with month-over-month comparison.

📄 Detailed steps → [references/task-query-traffic.md](references/task-query-traffic.md)

### Task 3: Query Total Requests (with MoM Comparison)

Query total requests (sum of GET/PUT/POST/DELETE/HEAD) via CES ShowMetricData, with month-over-month comparison.

📄 Detailed steps → [references/task-query-requests.md](references/task-query-requests.md)

---

## Core Commands

| Command | Description |
|---------|-------------|
| `hcloud obs ls` | List all buckets (obsutil mode); filter by region via `grep` |
| `hcloud CES ShowMetricData --region=<R> --namespace=SYS.OBS --metric_name=<M> --dim.0=bucket_name,<B> --period=86400 --filter=<F> --from=<ms> --to=<ms>` | Query CES metric data |
| `hcloud OBS GetBucketStorageInfo --region=<R> --bucket=<B>` | Get bucket capacity & object count (may not be supported; fallback: `obsutil ls obs://<B> -limit=0 -s`) |
| `python3 scripts/obs_traffic_stats.py --region <R> --bucket <B> (--period <P> \| --from <D> --to <D>) [--direction download\|upload\|both]` | Traffic statistics with MoM |
| `python3 scripts/obs_request_stats.py --region <R> --bucket <B> (--period <P> \| --from <D> --to <D>) [--include-errors]` | Request statistics with MoM |

> **⚠️ CES `ShowMetricData` does not support `--User-Agent`; appending it causes errors.**

> **Common CES metrics:**
>
> | Metric | `--metric_name` | `--filter` |
> |--------|----------------|------------|
> | Bucket capacity | `capacity_total` | `average` |
> | Extranet download traffic | `download_traffic_extranet` | `sum` |
> | Intranet download traffic | `download_traffic_intranet` | `sum` |
> | GET / PUT / POST / DELETE / HEAD requests | `get_request_count` / `put_request_count` / `post_request_count` / `delete_request_count` / `head_request_count` | `sum` |

---

## Parameter Confirmation

> **Before executing any task, the following parameters must be confirmed with the user. Guessing is prohibited.**

|| Parameter | Required/Optional | Description | Default ||
|| ----------- | ------------------ | ------------- | --------- ||
|| `--region` | Required | Huawei Cloud region (e.g., `cn-south-1`, `cn-north-4`); must be explicitly provided by the user | - ||
|| Bucket name | Required | OBS bucket name; dimension format: `--dim.0=bucket_name,<BucketName>` | - ||
|| Time range | Required | Must precisely match user's wording: "this month" ≠ "last 30 days" (see table below) | - ||
|| obsutil credentials | Required | Check via `hcloud obs ls -limit=1` before any OBS operation | - ||
|| `--direction` | Optional | Traffic direction: `download` / `upload` / `both` | `download` ||
|| `--include-errors` | Optional | Also query 4xx/5xx error request counts | `false` ||

> **Time range disambiguation:**
>
> | User's wording | Time range |
> |---------|------|
> | "this month" | 1st of current month 00:00:00 ~ now |
> | "last 30 days" / "past month" | now - 30 days ~ now |
> | "last month" | 1st of last month 00:00:00 ~ last day of last month 23:59:59 |
> | Specific date range | User-specified start and end times |

---

## Script Tools

This skill provides the following Python scripts that encapsulate best practices for traffic and request statistics:

### obs_traffic_stats.py — Download/Upload Traffic Statistics

```bash
# Last 30 days download traffic
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period last_30d

# This month download + upload traffic
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month --direction both

# Custom date range
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20
```

### obs_request_stats.py — Total Request Statistics

```bash
# Last 30 days request count
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period last_30d

# This month request count (with 4xx/5xx error stats)
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month --include-errors

# Custom date range
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20
```

The scripts incorporate key lessons learned: traffic vs. bandwidth metrics, hcloud dimension parameter format, precise time range matching, OBS lacking a single request_count metric, etc.

---

## Verification Method

See [references/verification-method.md](references/verification-method.md) for details.

**Quick validation:**
```bash
# Check OBS bucket list (using obsutil)
hcloud obs ls -limit=1

# Check obsutil configuration
obsutil ls -limit=1

# Validate traffic stats script
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket <BucketName> --period last_30d

# Validate request stats script
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket <BucketName> --period last_30d
```

---

## References

| Document | Description |
|----------|-------------|
| [task-list-buckets-with-stats.md](references/task-list-buckets-with-stats.md) | Task 1: List buckets with capacity and object counts |
| [task-query-traffic.md](references/task-query-traffic.md) | Task 2: Query download traffic with MoM |
| [task-query-requests.md](references/task-query-requests.md) | Task 3: Query total requests with MoM |
| [related-apis.md](references/related-apis.md) | API and CLI command details |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [obs-metrics.md](references/obs-metrics.md) | OBS CES monitoring metrics reference |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/error pattern comparison |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and practical experience |
| [obs_traffic_stats.py](scripts/obs_traffic_stats.py) | Traffic statistics script |
| [obs_request_stats.py](scripts/obs_request_stats.py) | Request statistics script |
