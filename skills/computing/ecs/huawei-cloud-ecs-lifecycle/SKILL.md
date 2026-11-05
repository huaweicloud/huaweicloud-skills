---
name: huawei-cloud-ecs-lifecycle
description: |
  Manage the full lifecycle of Huawei Cloud ECS (Elastic Cloud Server) instances — create, list, show
  details, start, stop, reboot, rename, delete, reinstall or switch the operating system, and resize
  (change flavor) cloud servers — plus basic ECS knowledge Q&A.
  Covers CRUD, power-state orchestration (start/stop/reboot) with batch support, OS reinstall/change,
  flavor resize, pagination, and filters. A Step 0 preflight check validates the KooCLI installation,
  credentials, and region before anything runs. All mutating operations require explicit user
  confirmation before execution.
  Triggers include: "创建云服务器", "删除云服务器", "启动云服务器", "停止云服务器", "重启云服务器",
  "修改云服务器名称", "查询云服务器列表", "查询云服务器详情", "重装操作系统", "切换操作系统",
  "变更云服务器规格", "ECS生命周期管理", "ECS运维",
  "create ecs", "delete ecs", "start ecs", "stop ecs", "reboot ecs", "reinstall os", "resize ecs",
  "change flavor", "ecs lifecycle", "弹性云服务器管理", "云服务器增删改查".
tags: [huawei-cloud, ecs, lifecycle, management, computing]
---

# Huawei Cloud ECS Lifecycle Management

> Full lifecycle management for Huawei Cloud Elastic Cloud Server (ECS) — from provisioning to
> decommissioning, including power-state orchestration and instance queries.

## Overview

This Skill manages the complete lifecycle of ECS (Elastic Cloud Server) instances on Huawei Cloud
using the KooCLI `ECS` service (with the `huaweicloudsdkecs` Python SDK as fallback):

| Capability | Operations | Actions |
| ------------ | ----------- | --------- |
| **Query** | `ListServersDetails`, `ShowServer` | List instances with filters/pagination; show instance detail |
| **Create** | `CreateServers` | Create one or more pay-per-use cloud servers |
| **Power state** | `BatchStartServers`, `BatchStopServers`, `BatchRebootServers` | Start / stop / reboot (batch) |
| **Update** | `BatchUpdateServersName` | Rename one or more servers |
| **OS image** | `ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit`, `ChangeServerOsWithCloudInit` / `ChangeServerOsWithoutCloudInit` | Reinstall the operating system, or switch the instance to a different OS image |
| **Resize** | `ListResizeFlavors`, `ResizeServer`, `ResizePostPaidServer`, `BatchResizeServers` | Query the flavors a server may be resized to; change the flavor (vCPU / memory) of one or many servers |
| **Delete** | `DeleteServers` | Delete one or more servers (optional EIP/data volume release) |
| **Knowledge** | — | Basic ECS FAQ (flavors, billing, auth, network, disk) answered inline |

**Scope note:** All mutating operations (create / delete / start / stop / reboot / rename / reinstall
OS / change OS / resize) are executed **only after explicit user confirmation**. Query operations are
safe to run anytime. Reinstall OS, change OS, and resize are **destructive or disruptive** — see
`references/lifecycle-change-operations.md` for the full sequence, parameters, and warnings.

## Prerequisites

1. **KooCLI (hcloud)** installed and authenticated — see `references/cli-installation-guide.md`.
   ⚠️ This is **verified at runtime by the Step 0 preflight check, not merely assumed**: if `hcloud`
   is missing from `PATH`, unauthenticated, or no region can be resolved, the run aborts before any
   ECS command is attempted.
2. **Region** — pass `--cli-region=cn-north-4` (use the account's region; e.g. `cn-north-4`), or the active CLI profile default is used
3. **IAM permissions** — the authenticated account needs the ECS permissions listed in
   `references/iam-policies.md` (least privilege); OS reinstall/change and resize additionally need
   the change-operation permissions documented there
4. **Python 3.8+** with `huaweicloudsdkecs` (only needed for the SDK fallback path)

### Quality Reporting Environment Variables

| Environment Variable | Required | Description |
| --------------------- | ---------- | ------------- |
| `SKILL_QUALITY_ENDPOINT` | No | 上报地址，默认 https://skillsapi.developer.myhuaweicloud.com/api/quality/report |
| `SKILL_QUALITY_GUEST_ENDPOINT` | No | Guest (unauthenticated) report endpoint |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set `1` to disable reporting (local debugging) |
| `SKILL_QUALITY_TIMEOUT` | No | Report timeout in seconds (default 3) |

## Workflow

0. **Preflight — mandatory entry check.** Run the preflight script *before* anything else:

   ```bash
   bash scripts/preflight_check.sh --region={region}
   ```

   It checks, in order: (1) `hcloud` is on `PATH`, (2) `hcloud version` runs, (3) credentials are
   configured, (4) the region is resolvable — then performs a read-only smoke call to prove the
   credentials actually work. **If any check fails, stop here**, print the installation /
   authentication guidance from `references/cli-installation-guide.md`, and do not attempt any ECS
   command. Use `--skip-auth-check` only for a deliberately offline run. This step exists precisely
   so that a missing binary or an unauthenticated account fails immediately at the entry point
   instead of surfacing as `command not found` in the middle of an operation. Exit codes:
   `0` = environment ready, `1` = not ready (**abort the workflow**), `2` = invalid usage.
1. **Classify the request** — knowledge question (answer inline from the Overview/FAQ below and
   official docs) or an ECS operation.
2. **Resolve the target server(s)** — for instance-specific operations, get `server_id` from the
   user, or list instances first (`ListServersDetails`) if the ID is unknown.
3. **Query operations** — build the command with the requested filters and execute directly.
4. **Mutating operations** — present the exact command and parameters to the user, **wait for
   explicit confirmation**, then execute. If the CLI fails (e.g. SDK/permission error), fall back
   to the `huaweicloudsdkecs` SDK equivalent.
5. **Report** — return the operation result (job ID, affected instance IDs, or detailed instance
   info) and, for state-change operations, suggest verifying with `ListServersDetails`.

## Core Commands

> All commands below use `--cli-region=cn-north-4` as the example region; use the
> authenticated account's region instead (or rely on the CLI profile default).
> Required parameters are always shown; the most common optional parameters are
> included. Parameter names were verified against the KooCLI `--help` output of
> each ECS operation. Example names/IDs are placeholders to be replaced with
> real values from the user's environment.

### List ECS instances

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=25 --name=my-ecs --status=ACTIVE
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved from credentials |
| `--limit` | No | integer | Page size, default 25, max 1000 |
| `--offset` | No | integer | Page number, >= 0 (0 == page 1), default 1 |
| `--name` | No | string | Instance name, fuzzy match (e.g. `--name=my-ecs`) |
| `--status` | No | string | ACTIVE / BUILD / SHUTOFF / REBOOT / ERROR / ... |
| `--flavor` | No | string | Flavor ID filter |
| `--ip` / `--ip_eq` | No | string | IPv4 fuzzy / exact match |
| `--server_id` | No | string | Exact IDs, comma-separated (<=100), exclusive with other filters |
| `--enterprise_project_id` | No | string | EP filter; `all_granted_eps` = all enterprise projects |
| `--tags` / `--not-tags` | No | string | Tag filter |
| `--marker` | No | string | Pagination marker (last server id of previous page) |

### Show ECS instance detail

```bash
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--server_id` | Yes | string | 云服务器ID (UUID) |

### Create ECS instance(s)

> **Confirmation required before execution.** Creating instances incurs billing.

```bash
hcloud ECS CreateServers --cli-region=cn-north-4 --server.name=my-ecs --server.flavorRef=s6.large.2 \
  --server.imageRef=9c2f377e-7f3a-4f4e-9c1a-2b3c4d5e6f7a --server.vpcid=81a7f347-8f0e-4b2a-9c4d-5e6f7a8b9c0d \
  --server.nics.1.subnet_id=04e00f59-1a2b-3c4d-5e6f-7a8b9c0d1e2f --server.root_volume.volumetype=SSD \
  --server.security_groups.1.id=41a937e1-9b8c-7d6e-5f4a-3b2c1d0e9f8a --server.availability_zone=cn-north-4a \
  --server.count=1 --server.adminPass=Huawei@123
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--server.name` | Yes | string | Instance name (1-64 chars) |
| `--server.flavorRef` | Yes | string | Flavor ID (e.g. `s6.large.2`), query via `ListFlavors` |
| `--server.imageRef` | Yes | string | Image ID (UUID), query via IMS `ListImages` |
| `--server.vpcid` | Yes | string | VPC ID (UUID) |
| `--server.root_volume.volumetype` | Yes | string | Root disk type: SATA/SAS/SSD/GPSSD/ESSD/... |
| `--server.nics.1.subnet_id` | Yes (in practice) | string | Subnet ID under the VPC; required unless the VPC default subnet is used |
| `--server.security_groups.1.id` | Yes (in practice) | string | Security group ID; commonly required by the API's VPC configuration |
| `--server.availability_zone` | No | string | AZ (e.g. `cn-north-4a`) |
| `--server.count` | No | integer | Number to create (default 1) |
| `--server.adminPass` | No | string | Initial admin password (or `--server.key_name` for keypair) |
| `--dry_run` | No | boolean | Pre-check without actually creating |

> **Note:** Both parameters above are marked **Yes (in practice)**. They are optional at the API
> schema level, but in practice omitting them fails ECS creation in most VPC configurations:
> `--server.nics.[N].subnet_id` is required unless the VPC default subnet is used, and
> `--server.security_groups.[N].id` is commonly required by the API's VPC configuration.
> For pay-per-use only: `CreateServers` with `--server.extendparam.chargingMode=0`; use
> `CreatePostPaidServers` for a simpler pay-per-use flow if preferred.

### Delete ECS instance(s)

> **Confirmation required before execution.** Data on disks may be lost when `--delete_volume=true`.

```bash
hcloud ECS DeleteServers --cli-region=cn-north-4 --servers.1.id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c --delete_publicip=false --delete_volume=false
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--servers.[N].id` | Yes | string | Server IDs, indexed form (`--servers.1.id=...`), max 1000 |
| `--delete_publicip` | No | boolean | Also delete bound EIP (default false) |
| `--delete_volume` | No | boolean | Also delete attached data volumes (default false) |

### Start ECS instance(s)

> **Confirmation required before execution.**

```bash
hcloud ECS BatchStartServers --cli-region=cn-north-4 --os-start.servers.1.id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--os-start.servers.[N].id` | Yes | string | Server IDs, indexed form, max 1000 |

### Stop ECS instance(s)

> **Confirmation required before execution.** `HARD` stop may lose unsaved data.

```bash
hcloud ECS BatchStopServers --cli-region=cn-north-4 --os-stop.servers.1.id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c --os-stop.type=SOFT
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--os-stop.servers.[N].id` | Yes | string | Server IDs, indexed form, max 1000 |
| `--os-stop.type` | No | string | `SOFT` (default, graceful) or `HARD` (forced) |

### Reboot ECS instance(s)

> **Confirmation required before execution.** `HARD` reboot may lose unsaved data.

```bash
hcloud ECS BatchRebootServers --cli-region=cn-north-4 --reboot.servers.1.id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c --reboot.type=SOFT
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--reboot.servers.[N].id` | Yes | string | Server IDs, indexed form, max 1000 |
| `--reboot.type` | Yes | string | `SOFT` (graceful) or `HARD` (forced) |

### Rename ECS instance(s)

> **Confirmation required before execution.**

```bash
hcloud ECS BatchUpdateServersName --cli-region=cn-north-4 --name=my-ecs-renamed --servers.1.id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--name` | Yes | string | New name (<=64 chars); batch rename applies same name to all |
| `--servers.[N].id` | Yes | string | Server IDs, indexed form, max 1000 |
| `--dry_run` | No | boolean | Pre-check without applying the change |

### Reinstall the operating system

> **Confirmation required before execution.** Reinstalling the OS **reinitializes the system disk**
> and reboots the instance — data on the system disk is lost. Stop the server first
> (`BatchStopServers`).

```bash
# Cloud-Init variant (supports user_data injection)
hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.adminpass={admin_pass}

# Without Cloud-Init (no metadata.user_data parameter)
hcloud ECS ReinstallServerWithoutCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.keyname={key_name}
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-reinstall.adminpass` | No | string | New admin password (8-26 chars, complexity rules) |
| `--os-reinstall.keyname` | No | string | Keypair name for login |
| `--os-reinstall.userid` | No | string | User ID that owns the server |
| `--os-reinstall.mode` | No | string | `withStopServer` — stop, reinstall, then start |
| `--os-reinstall.metadata.user_data` | No | string | Cloud-Init user data (**`WithCloudInit` only**) |

> Reinstalling does **not** change the image. To switch to a *different* OS image use
> `ChangeServerOsWithCloudInit` instead.

### Change the operating system image

> **Confirmation required before execution.** Switching the OS also **reinitializes the system
> disk**; stop the server first.

```bash
hcloud ECS ChangeServerOsWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-change.imageid={image_id} --os-change.adminpass={admin_pass}
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-change.imageid` | Yes | string | Target image ID (UUID), query via IMS `ListImages` |
| `--os-change.adminpass` | No | string | New admin password |
| `--os-change.keyname` | No | string | Keypair name for login |
| `--os-change.isAutoPay` | No | string | `true`/`false` — auto-pay when the OS change is billed on a yearly/monthly instance |
| `--os-change.mode` | No | string | `withStopServer` — stop, change, then start |
| `--os-change.metadata.user_data` | No | string | Cloud-Init user data (**`WithCloudInit` only**) |

> The `WithoutCloudInit` variant (`ChangeServerOsWithoutCloudInit`) has no
> `--os-change.metadata.user_data` parameter.

### Resize (change flavor)

> **Confirmation required before execution.** Resizing restarts the instance. Always run the
> `--dry_run=true` pre-check first, then confirm and re-run without it.

```bash
# 1. Query the flavors this server may be resized to
hcloud ECS ListResizeFlavors --cli-region={region} --instance_uuid={server_id}

# 2. Pre-check, no change is made
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --resize.mode=withStopServer --dry_run=true

# 3. Apply after user confirmation (drop --dry_run)
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --resize.mode=withStopServer
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--resize.flavorRef` | Yes | string | Target flavor ID, must appear in `ListResizeFlavors` |
| `--resize.mode` | No | string | `withStopServer` — allows resizing a running server (auto stop/start) |
| `--resize.extendparam.isAutoPay` | No | string | `true`/`false` — auto-pay for a yearly/monthly resize |
| `--resize.dedicated_host_id` | No | string | New dedicated host ID (DeH only) |
| `--resize.cpu_options.hw:cpu_threads` | No | integer | `1` = disable hyper-threading, `2` = enable |
| `--dry_run` | No | boolean | Pre-check only; no change is made |

> `ResizePostPaidServer` (pay-per-use) and `BatchResizeServers` (batch, `--resize.servers.[N].id`)
> are also available. They do **not** share one parameter set: `ResizePostPaidServer` accepts
> `--dry_run` and `--resize.mode` but **not** `--resize.dedicated_host_id` or
> `--resize.extendparam.isAutoPay`; `BatchResizeServers` accepts `--resize.mode`,
> `--resize.cpu_options.hw:cpu_threads` and `--resize.promotion.*` but **not** `--dry_run`.
> Always confirm the accepted parameters with `hcloud ECS <Operation> --help`.

> **Full parameter tables, the complete stop→change→verify sequence, and the mapping from the
> operation names commonly (but incorrectly) assumed — `ReinstallOs`, `ChangeServerFleet` — to the
> real KooCLI operations are in `references/lifecycle-change-operations.md`.**

## Parameter Confirmation

| Command | Required Parameters (besides `--cli-region`) |
| --------- | ---------------------------------------------- |
| `ListServersDetails` | none (filters optional) |
| `ShowServer` | `--server_id` |
| `CreateServers` | `--server.name`, `--server.flavorRef`, `--server.imageRef`, `--server.vpcid`, `--server.root_volume.volumetype` |
| `DeleteServers` | `--servers.[N].id` |
| `BatchStartServers` | `--os-start.servers.[N].id` |
| `BatchStopServers` | `--os-stop.servers.[N].id` |
| `BatchRebootServers` | `--reboot.servers.[N].id`, `--reboot.type` |
| `BatchUpdateServersName` | `--name`, `--servers.[N].id` |
| `ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit` | `--server_id` |
| `ChangeServerOsWithCloudInit` / `ChangeServerOsWithoutCloudInit` | `--server_id`, `--os-change.imageid` |
| `ListResizeFlavors` | none (filters optional) |
| `ResizeServer` / `ResizePostPaidServer` | `--server_id`, `--resize.flavorRef` |
| `BatchResizeServers` | `--resize.servers.[N].id`, `--resize.flavorRef` |

`--project_id` is auto-resolved by KooCLI from the authenticated credentials; `--cli-region` is the
only parameter the agent must always supply explicitly.

## Basic ECS FAQ (Knowledge Q&A)

- **What is ECS?** Elastic Cloud Server — Huawei Cloud's IaaS compute service. Instances can be
  provisioned in minutes with flexible flavors, images, disks, and networks.
- **Flavors** — defined by vCPUs/memory (e.g. `s6.large.2` = 2 vCPU / 4 GB). Query
  available flavors via `hcloud ECS ListFlavors --cli-region=cn-north-4`.
- **Billing** — pay-per-use (按需) or yearly/monthly (包年/包月); spot instances (竞价) available.
- **Login** — keypair (recommended) or password. For password login the initial password is set at
  creation (`adminPass` / `user_data`).
- **Status values** — `ACTIVE` (running), `SHUTOFF` (stopped), `BUILD` (creating), `REBOOT`,
  `ERROR`, `MIGRATING`, `RESIZE`, `SHELVED`, `DELETED`.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for ECS lifecycle operations
- `references/cli-installation-guide.md` — KooCLI installation, authentication, and the Step 0 preflight check
- `references/verification-method.md` — How to verify each operation
- `references/lifecycle-change-operations.md` — Reinstall / change OS and resize: verified operations, parameters, sequences, and the `ReinstallOs` / `ChangeServerFleet` name mapping
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria for this skill

## KooCLI Command Format Standard

Every KooCLI command is built as: `hcloud` + service name (`ECS`) + operation name
(PascalCase) + region parameter `--cli-region=<region>` + parameter key-value pairs
(`--key=value`). Only the executable examples in [Core Commands](#core-commands)
are meant to be run directly.

| Feature | Description | Example |
| --------- | ------------- | --------- |
| Service name | KooCLI service name (detected from metadata: `ecs` → invoked as `ECS`) | `ECS` |
| Operation name | PascalCase | `ListServersDetails` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--server_id=xxx` |
| Indexed parameter | `--key.N=value` | `--servers.1.id=xxx` |

## Edge Cases

| Scenario | Handling |
| ---------- | ---------- |
| Unknown `server_id` / empty query result | Return "no ECS instance matches" and suggest listing first |
| `--server_id` combined with other filters | `server_id` wins; other filters ignored (CLI behavior) |
| Create without subnet/security group | Explain that VPC networking config is needed; confirm before executing |
| User asks to delete an ACTIVE server | Warn about data loss, require explicit confirmation |
| `--limit` > 1000 | CLI rejects; keep <= 1000 (default 25) |
| Stop/reboot with unsaved work | Prefer `SOFT`; explain `HARD` data-loss risk and confirm |
| CLI failure (auth/permission) | Fall back to `huaweicloudsdkecs` SDK; report the underlying error |
| No region specified | Use the active CLI profile default region; if that is empty too, the Step 0 preflight fails with guidance rather than silently picking one |
| `hcloud` missing from `PATH`, or no usable credentials | Step 0 preflight aborts with actionable install/auth guidance — never proceed to an ECS command |
| Reinstall / change OS on a running server | Stop it first (`BatchStopServers`), or pass `--os-reinstall.mode=withStopServer` / `--os-change.mode=withStopServer` |
| Reinstall / change OS requested | Warn that the **system disk is reinitialized** and data is lost; require explicit confirmation |
| Resize a running server | Pass `--resize.mode=withStopServer` so the platform stops and restarts it |
| Target flavor not offered for this instance | Run `ListResizeFlavors --instance_uuid={server_id}` first; a flavor absent from that list is rejected |
| Resize before committing | Always run `--dry_run=true` first; it validates the request without changing the instance |
| Assumed operation name `ReinstallOs` / `ChangeServerFleet` | These do **not** exist in KooCLI; use the real operations listed in `references/lifecycle-change-operations.md` |

## Quality Reporting

This Skill integrates [scripts/skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution
quality reporting. Every run reports trace_id, status (success/biz_fail/sys_fail/cancel), error
code, cost, and masked input/output.

### Integration

- **Python entry point:** wrap execution with `quality_context`:

  ```python
  from skill_quality_sdk import quality_context
  with quality_context(skill_name="huawei-cloud-ecs-lifecycle") as q:
      q.input = {"operation": "ListServersDetails", "region": "cn-north-4"}
      result = run_ecs_operation()
      q.output = result
  ```

- **CLI self-check:** `python3 scripts/skill_quality_sdk.py` (sends one test report).

### Error Code Convention

| Prefix | Category | Examples |
| ------ | -------- | -------- |
| U | User input | U01 missing param, U03 no data |
| C | Config | C01 missing AK/SK |
| N | Network | N01 timeout |
| B | Code bug | B01 null pointer |
| P | Platform | P01 scheduler error |

Non-blocking, fail-silent. Disable with `SKILL_QUALITY_DISABLE=1` for local testing.
