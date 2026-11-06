---
name: huawei-cloud-obs-dir-count
description: |
  Count the number of directories (folders) in a Huawei Cloud OBS (Object Storage Service)
  bucket or under a bucket prefix, returning the count as an integer. Read-only: never
  creates, modifies, deletes, or uploads any bucket or object. Uses the `hcloud OBS ls -d`
  command (obsutil) with strict input validation.
  Triggers include: "count OBS directories", "how many folders are in the OBS bucket <bucket>",
  "number of directories under <prefix> in OBS bucket <bucket>", "统计OBS目录数量",
  "查询OBS目录数量", "数一下OBS桶里的文件夹数量", "count folders in an OBS bucket".
tags: ["huawei-cloud", "obs", "directory-count", "obs-count"]
---

# Huawei Cloud OBS Directory Count Skill

## Overview

Count the number of directories (folders) in a Huawei Cloud OBS bucket or under a
bucket prefix. The skill executes a read-only listing (`hcloud OBS ls <url> -d`, which
uses obsutil behind the scenes) and prints a single integer: the number of immediate
sub-directories under the target, or the total number of directories across all levels
when `--recursive` is used.

This is a **query-only** skill. It performs no create, modify, delete, or upload
operations on any bucket or object.

## Security Scope

> This skill is **read-only** and honors the principle of least privilege. It declares
> the following capability and permission bounds up front so execution never exceeds them.

| Dimension | Declaration |
|-----------|-------------|
| Allowed tools | `hcloud` (KooCLI) `OBS` module only, invoked by the bundled Python script `scripts/count_obs_directories.py`. No other tool is called. |
| Credential source | Read only from the user's own `obsutil` configuration file (`~/.obsutilconfig`) which the user sets once via `hcloud obs config -i=<AK> -k=<SK> -e=<endpoint>`. The script never reads, prints, or forwards AK/SK values. |
| Network endpoints | Only the OBS endpoint configured by the user in their `obsutil` config (e.g. `obs.cn-north-4.myhuaweicloud.com`). |
| Resource access | **Read-only**: `ListBuckets` and `ListObjects` are used solely to enumerate directories. The script never creates, modifies, deletes, or uploads any bucket or object. |
| Result output | A single integer count on stdout (or a JSON object with `--json`). On failure, an explanatory message is written to stderr and a non-zero exit code is returned. |
| No remote code execution | The script runs only local `hcloud OBS ls` commands with a fixed argv list and no shell. There is no `eval`, `exec`, dynamic import, or download-then-run of remote content. |

## Prohibited Operations (Security Constraints)

> **This skill strictly forbids the following operations, regardless of user requests:**

| Prohibited Operation | Reason |
|----------------------|--------|
| Delete a bucket / object / batch delete / empty bucket | Irreversible; the script only ever lists directories. |
| Create / upload / modify any object or bucket | Out of scope; this skill is query-only. |

> If a user asks for create/upload/delete, refuse and explain: "This skill only counts
> directories in an OBS bucket and does not create, upload, modify, or delete anything."

## Language Policy

- `SKILL.md` and all reference documents are written in English.
- The runtime script prints **English-first** messages, each followed by a concise Chinese
  `[提示]` hint. There is no requirement that Chinese text be present for success; the
  script succeeds by printing only the integer count.

## Prerequisites

> **Prerequisite 1/2: `hcloud` (KooCLI) CLI installed.**
> The `OBS` module (obsutil) is bundled with KooCLI. Verify it is present:
>
> ```bash
> hcloud help
> ```
>
> If `hcloud` is missing, follow `references/cli-installation-guide.md` for a **user-level,
> checksum-verified install** (never a root install of an unverified download).

> **Prerequisite 2/2: `obsutil` credentials configured for hcloud OBS.**
> Before any OBS operation the script requires the user's AK/SK and endpoint to be set in
> their own obsutil configuration. Check it with:
>
> ```bash
> hcloud OBS ls -limit=1
> ```
>
> If the response is `Please set ak, sk and endpoint in the configuration file!` or an
> authentication error, configuration is missing. The user must run, **in their own
> terminal** (never paste AK/SK into the conversation):
>
> ```text
>   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<region>.myhuaweicloud.com
> ```
>
> Example (cn-north-4): `hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.cn-north-4.myhuaweicloud.com`
>
> Then retry.

## Authentication

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing AK/SK values in any form.
> - **Prohibited** from asking the user to enter AK/SK directly in the conversation.
> - **Prohibited** from using `hcloud configure set` or `obsutil config` with literal
>   credential values on the command line (they would leak into shell history).
> - Only allowed to read credentials from the user's pre-configured `obsutil` config file
>   or from `HUAWEI*`/`HW*`/`HWC*` environment variables.
>
> If a user offers AK/SK in chat, politely refuse and ask them to configure it out-of-band
> following the Prerequisites section, then retry.

## IAM Permission Policies

Ensure the IAM user holds OBS **read-only** permissions. See
`references/iam-policies.md` for full policy JSON.

**Minimum required permissions:**
- `obs:bucket:ListAllMyBuckets` — list buckets (v3) / `obs:bucket:listAllMyBuckets` (v5)
- `obs:bucket:ListBucket` — list objects (v3) / `obs:bucket:listBucket` (v5)
- `obs:bucket:GetBucketMetadata` — bucket attributes (v3) / `obs:bucket:getBucketMetadata` (v5)

## Workflow

> Every run requires explicit user confirmation of the target **before** any listing
> executes. The skill never guesses a bucket or prefix.

1. **Confirm target.** Ask the user to confirm the OBS bucket name and (optionally) the
   prefix. Confirm whether the count is for **immediate sub-directories** or **all levels
   (recursive)**.
2. **Preflight.** Verify `hcloud` is present and `hcloud OBS ls -limit=1` returns data
   (credentials configured). If not, guide the user through the Prerequisites section.
3. **Run the count.** Execute:
   ```bash
   python3 scripts/count_obs_directories.py --bucket <bucket> [--prefix <prefix>] [--recursive]
   ```
4. **Return result.** Relay the returned integer (or JSON) to the user. On failure, the
   script writes an explanatory bilingual message to stderr; relay that message and the
   fix suggestion. Do not claim success when the script exited non-zero.

## Core Commands

| Command | Description |
|---------|-------------|
| `hcloud OBS ls obs://<bucket> -d` | List buckets / immediate directories (obsutil syntax) |
| `python3 scripts/count_obs_directories.py --bucket <bucket>` | Count immediate sub-directories under the bucket root |
| `python3 scripts/count_obs_directories.py --bucket <bucket> --prefix <prefix>` | Count immediate sub-directories under `<prefix>` |
| `python3 scripts/count_obs_directories.py --bucket <bucket> --recursive` | Count all directories at every level under the bucket |
| `python3 scripts/count_obs_directories.py --bucket <bucket> --prefix <prefix> --recursive` | Count all directories at every level under `<prefix>` |
| `python3 scripts/count_obs_directories.py --bucket <bucket> --json` | Count and print a JSON object (machine-readable) |

> `--recursive` accepts `--max-depth <N>` to bound traversal depth (`0` = unlimited).
> All examples require credentials configured per the Prerequisites section.

## Parameter Confirmation

> **Before executing, confirm the following parameters with the user. Guessing is prohibited.**

| Parameter | Required/Optional | Description |
|-----------|-------------------|-------------|
| `--bucket` | Required | OBS bucket name (lowercase letters, digits, `.` and `-`; 3-63 chars). |
| `--prefix` | Optional | Folder path inside the bucket (letters, digits, `.` `_` `/` `-` only; must not start/end with `/`). |
| `--recursive` | Optional | Count directories at every level below the target instead of only immediate sub-directories. |
| `--max-depth` | Optional | With `--recursive`, bound traversal depth (`0` = unlimited). |
| obsutil credentials | Required | Must be configured before any listing; see Prerequisites. |

## KooCLI Command Format Standard

`hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]`

| Feature | Notes |
|---------|-------|
| Service / Operation | KooCLI service names are title-case (e.g. `OBS` `ECS`) and operations are PascalCase. |
| OBS module note | The `hcloud OBS` module exposes obsutil-style commands such as `hcloud OBS ls`, where the verb is lowercase (`ls`) and there is no `--cli-region` (the region is fixed by the user's obsutil endpoint). These are intentionally not KooCLI service/operation forms. |
| This skill | Uses `hcloud OBS ls` (obsutil syntax) only. There is no separate `--cli-region` parameter; region comes from the configured obsutil endpoint. |

## Script Tool

The skill bundles one runtime script:

| Script | Description |
|--------|-------------|
| `scripts/count_obs_directories.py` | Counts directories (immediate or recursive) in the target bucket/prefix. Strict input validation, read-only, bilingual errors. |

## Verification Method

See `references/verification-method.md` for full details.

**Quick validation:**
```bash
# 1) Confirm obsutil credentials are configured
hcloud OBS ls -limit=1

# 2) Count immediate directories in a bucket
python3 scripts/count_obs_directories.py --bucket <bucket>

# 3) Count immediate directories under a prefix
python3 scripts/count_obs_directories.py --bucket <bucket> --prefix <prefix>

# 4) Count all directories recursively
python3 scripts/count_obs_directories.py --bucket <bucket> --recursive

# 5) Input validation rejects malicious input (non-zero exit, no shell execution)
python3 scripts/count_obs_directories.py --bucket 'bad;name'; echo $?
```

## References

| Document | Description |
|----------|-------------|
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct vs. incorrect behavior and output patterns |
| [cli-installation-guide.md](references/cli-installation-guide.md) | User-level, checksum-verified install of hcloud / obsutil |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow of a directory-count run |
| [iam-policies.md](references/iam-policies.md) | Least-privilege read-only IAM policies |
| [related-commands.md](references/related-commands.md) | OBS listing CLI/SDK details and counting notes |
| [troubleshooting.md](references/troubleshooting.md) | Common problems and their fixes |
| [verification-method.md](references/verification-method.md) | Step-by-step verification and testing |