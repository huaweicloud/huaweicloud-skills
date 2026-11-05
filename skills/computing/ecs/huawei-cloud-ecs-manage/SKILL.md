---
name: huawei-cloud-ecs-manage
description: |
  Use when managing Huawei Cloud ECS (Elastic Cloud Server / 弹性云服务器) instances —
  lifecycle management (create / start / stop / restart / delete), day-to-day change
  operations (resize / reinstall OS / reset password / replace keypair / bind & unbind EIP /
  change security group / add & remove NIC / attach & detach volume), instance querying,
  quota/flavor/image inspection, mandatory async-job polling after every write, and
  multi-step root-cause diagnosis of ECS instance creation failures
  (quota → flavor → image → network → keypair → disk).
  Provides 23 huawei_* actions: huawei_list_ecs_instances, huawei_get_ecs_instance,
  huawei_list_ecs_flavors, huawei_list_ecs_images, huawei_list_ecs_quotas,
  huawei_diagnose_ecs_create_failure, huawei_analyze_ecs_health, huawei_create_ecs_instance,
  huawei_start_ecs_instance, huawei_stop_ecs_instance, huawei_restart_ecs_instance,
  huawei_delete_ecs_instance, huawei_resize_ecs_instance, huawei_reinstall_ecs_os,
  huawei_reset_ecs_password, huawei_replace_ecs_keypair, huawei_bind_ecs_eip,
  huawei_unbind_ecs_eip, huawei_change_ecs_security_group, huawei_add_ecs_nic,
  huawei_remove_ecs_nic, huawei_attach_ecs_volume, huawei_detach_ecs_volume.
  Service keywords: ECS, elastic cloud server, instance, VM, server, flavor, image, quota,
  keypair, security group, subnet, EIP, job, resize, reinstall, 云服务器, 弹性云服务器, 实例,
  规格, 镜像, 配额, 密钥对, 安全组, 子网, 创建失败, 启动, 停止, 重启, 删除, 变更规格, 重装系统,
  重置密码, 绑定EIP, 解绑EIP, 网卡, 挂载磁盘, 卸载磁盘, 异步任务.
  Triggers include: "ECS 创建失败", "云服务器创建失败", "创建云主机失败", "ECS 创建不了",
  "create ECS failed", "instance creation failed", "创建云服务器", "启动云服务器",
  "停止云服务器", "重启云服务器", "删除云服务器", "ECS 规格", "ECS 配额", "ECS 镜像",
  "list ECS instances", "diagnose ECS", "ECS health", "ecs create diagnose",
  "ECS 变更规格", "云服务器升配", "ECS 重装系统", "重置云服务器密码", "更换密钥对",
  "绑定弹性公网IP", "解绑EIP", "更换安全组", "添加网卡", "删除网卡", "挂载云硬盘",
  "卸载云硬盘", "ECS resize", "reinstall ECS OS", "async job polling".
tags: [huawei-cloud, ecs, compute, diagnose, management]
---

# Huawei Cloud ECS Manage (Create-Failure Diagnosis & Instance Management)

**STOP - Do not answer from general knowledge. Follow the procedure below.**


<!-- cli-install-version: 3.9.0 -->
## Step 0: Ensure skill-quality-cli (required; installed on first use)

```bash
bash scripts/ensure_cli.sh   # idempotent: installs only if absent (no auto-upgrade)
export PATH="$HOME/.local/bin:$PATH"
skill-quality-cli version    # verify it works
```

> **Run this step first**: quality reporting depends on `skill-quality-cli`, ensured
> idempotently by `scripts/ensure_cli.sh` (installs once if missing, skips if present;
> **no auto-upgrade** — run `skill-quality-cli upgrade` to update manually).
> If offline or the download fails, the skill degrades silently (business flow unaffected);
> re-run this step once back online.
Always run `hcloud ECS <Operation> --help` before constructing commands to discover exact
parameter names and requirements.

## Overview

This skill provides AI Agent capabilities for Huawei Cloud ECS (Elastic Cloud Server / 弹性云服务器):
instance lifecycle management (create/start/stop/restart/delete), instance/ quota/ flavor/ image
querying, and a **6-step create-failure root-cause diagnosis** that eliminates the most common causes
of "ECS instance creation failed" in order: **quota → flavor → image → network → keypair → disk**.

It exposes 23 `huawei_*` actions in five capability groups:

| Capability | Risk level | Actions |
| ---------- | ---------- | ------- |
| Query (read-only) | R3 — auto execute | `huawei_list_ecs_instances`, `huawei_get_ecs_instance`, `huawei_list_ecs_flavors`, `huawei_list_ecs_images`, `huawei_list_ecs_quotas` |
| Diagnose (read-only) | R3 — auto execute | `huawei_diagnose_ecs_create_failure`, `huawei_analyze_ecs_health` |
| Manage — lifecycle | R2 — preview + confirm | `huawei_create_ecs_instance`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`, `huawei_restart_ecs_instance` |
| Manage — lifecycle | R1 — preview + confirm | `huawei_delete_ecs_instance` |
| Manage — change operations (§5) | R2 — preview + confirm | `huawei_resize_ecs_instance`, `huawei_reinstall_ecs_os`, `huawei_reset_ecs_password`, `huawei_replace_ecs_keypair`, `huawei_bind_ecs_eip`, `huawei_change_ecs_security_group`, `huawei_add_ecs_nic`, `huawei_attach_ecs_volume`, `huawei_detach_ecs_volume` |
| Manage — change operations (§5) | R1 — preview + confirm | `huawei_unbind_ecs_eip`, `huawei_remove_ecs_nic` |

Every write action is **asynchronous**: the API returns a `job_id` and the real work continues in
the background. Polling that job is a **mandatory** post-step, not an optional extra — see
[§6 Async job polling](#6-async-job-polling-r3--mandatory-after-every-write).

**Scope boundaries:**

- ✅ Query ECS instances, flavors, images, quotas (read-only)
- ✅ Diagnose ECS create failures (quota → flavor → image → network → keypair → disk) and
  analyze instance health (status / disk / network)
- ✅ Create (post-paid), start, stop, restart, delete ECS instances (R2/R1: always preview + confirm)
- ✅ Change an **existing instance**: resize flavor, reinstall OS, reset password, replace keypair,
  bind/unbind EIP, attach/detach an existing security group, add/remove a NIC, attach/detach a volume
  (R2/R1: always preview + confirm)
- ❌ NEVER create, delete or reconfigure the VPC / subnet / security-group **resource** or the
  EVS **volume resource** itself. This skill only attaches or detaches existing resources to an
  instance; use the dedicated VPC / EVS skills for resource-level mutation.
- ❌ NEVER execute any write action without explicit user confirmation
- ❌ NEVER report a write as "done" before its async job reaches `SUCCESS` and, for `create`,
  before the instance reaches `ACTIVE`
- ❌ NEVER echo credentials (AK/SK, passwords, tokens) in any output or report
- ➡️ Out of scope: **RDS / database** queries. This skill manages compute only. When the user asks
  about a database that an ECS instance depends on, hand the question **back to the user** with a
  pointer to a dedicated RDS skill or the Huawei Cloud RDS console — this skill never invokes another
  skill. See `references/related-skills.md` for the hand-off wording.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli`
(installed by `scripts/ensure_cli.sh` if absent).

## Critical Warnings

| Trap | Why |
| ---- | --- |
| Quota exhaustion is the #1 create failure | `Insufficient quota` / `Quota exceeded` means instances/cores/RAM/volumes hit the project limit — check `ShowServerLimits` first |
| Flavor must exist **in the target region/AZ** | A flavor exists globally but may be sold out or unavailable in the chosen AZ — filter `ListFlavors` by `--availability_zone` |
| Image must be `active` and match the flavor architecture | Deleted/私有镜像 with wrong `__os_type`/`architecture` (x86 vs ARM) fails provisioning — check `IMS ListImages --status=active` |
| Subnet with no free IPs blocks create | If the subnet CIDR is exhausted or `dhcp` disabled, NIC allocation fails |
| Security group must exist before create | Referencing a non-existent security group ID fails the request |
| Keypair errors are misleading | If `key_name` is set but the keypair does not exist, creation fails with `KeypairNotFound` — verify with `KPS ListKeypairs` |
| Disk/AZ availability | Root/data volume types (SATA/SAS/GPSSD) may be unavailable in the target AZ — check `EVS ListVolumes` and volume quotas |
| Deletion is irreversible | R1: verify the instance first, confirm no data dependency, then require explicit user confirmation |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - Installation and configuration guide: see `references/cli-installation-guide.md`
   - Two supported authentication modes:
     - **AK/SK credentials**: environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
       (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`), or interactive setup via the hcloud configure wizard
     - **Local hcloud profile**: run "hcloud configure list"; it must show a valid profile with mode `AKSK`
       and a real `accessKeyId`
   - Verify authentication with "hcloud configure list"
2. **Region**: ECS is region-specific. Always pass `--cli-region={region}` (e.g. `cn-north-4`).
   `--project_id` is auto-filled from the profile when omitted.
3. **IAM permissions**: least-privilege policies are provided in `references/iam-policies.md`.
   - Query/diagnose: `ecs:cloudServers:list`, `ecs:cloudServers:get`, `ecs:cloudServerFlavors:list`,
     `ecs:cloudServerImages:list`, `ecs:jobs:get`, `ecs:serverVolumes:list`, `ims:images:list`,
     `vpc:subnets:list`, `vpc:securityGroups:list`, `vpc:publicIps:list`, `evs:volumes:list`,
     `kps:keypairs:list` (diagnosis step 5, `hcloud KPS ListKeypairs`)
   - Manage: `ecs:cloudServers:create`, `ecs:cloudServers:action` (start/stop/restart, resize,
     reinstall, reset password, NIC and security-group changes), `ecs:cloudServers:delete`
   - Change operations (§5) also need the write action of each resource they touch, e.g.
     `evs:volumes:delete` with `--delete_volume=true`, `vpc:publicIps:delete` with
     `--delete_publicip=true`; the exact list is in `references/iam-policies.md`.
4. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify target → region, instance_id / flavor_id / image_id / vpc_id / subnet_id / key_name, intent keywords
2. Classify intent →
     - Query/Diagnose (R3): list / show / analyze / diagnose — auto execute
     - Manage lifecycle (R2): create / start / stop / restart — ALWAYS show preview and ask for explicit confirmation
     - Manage lifecycle (R1): delete — ALWAYS show the instance details, irreversible warning, explicit confirmation
     - Manage change ops (R2): resize / reinstall / reset password / replace keypair / bind EIP /
       change security group / add NIC / attach volume — ALWAYS preview + confirm
     - Manage change ops (R1): unbind EIP / remove NIC / delete keypair — ALWAYS show the current
       attachment, irreversible warning, explicit confirmation
3. Preflight → for create and for every change op, run the relevant read-only checks first
   (quota, flavor, image, network, keypair, disk) so the user confirms against real state
4. Execute → build the hcloud command from the verified templates below
5. Capture the job id → the write API returns a job_id immediately; the work is still running
6. Poll async job → `hcloud ECS ShowJob` until `status=SUCCESS|FAIL`; for create ALSO poll
   `hcloud ECS ShowServer` until `status=ACTIVE`; then report the FINAL state to the user
7. Output → structured JSON summary + readable diagnosis report
8. Report quality → automatic via skill-quality-cli run wrapping (see Step 0 / Prerequisites #4)
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_ecs_instance`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`,
  `huawei_restart_ecs_instance`): show the full command, the target instance(s), and ask "confirm?"
  before running.
- **R1 action** (`huawei_delete_ecs_instance`): first run the read-only check
  (`ShowServer` to confirm the instance exists and record its status/flavor/volumes). Show the full
  command with the irreversible deletion warning, and require explicit confirmation before running.
- **Change-operation actions** (R2: `huawei_resize_ecs_instance`, `huawei_reinstall_ecs_os`,
  `huawei_reset_ecs_password`, `huawei_replace_ecs_keypair`, `huawei_bind_ecs_eip`,
  `huawei_change_ecs_security_group`, `huawei_add_ecs_nic`, `huawei_attach_ecs_volume`):
  show the **current** state (via `ShowServer` / `ListServerVolumeAttachments` / `ListServerInterfaces`),
  the full command and the expected end state, then ask "confirm?".
- **Change-operation actions** (R1: `huawei_unbind_ecs_eip`, `huawei_remove_ecs_nic`): show what will
  be detached and the connectivity impact (an unbound EIP loses public access; a removed NIC loses
  that network path and its private IP), require explicit confirmation, and never chain them with a
  delete. For `huawei_detach_ecs_volume` (R2) warn that `--delete_flag=1` deletes the data disk.
- **Create preflight**: before `huawei_create_ecs_instance`, ALWAYS run
  `huawei_diagnose_ecs_create_failure` (or at least the quota + flavor + image checks) so the user
  sees the environment is ready, then confirm.
- **Async polling is mandatory**: never close out a write action before the job reaches a terminal
  state. A `job_id` without polling is an **incomplete** action, not a success.

Write operations are marked `[W]` / 写操作 in the command blocks below (检测关键字:
create / start / stop / restart / delete — same verbs the test pipeline's write-operation detector keys on).

## Core Commands

> All commands below are shown in **dual form**: the bare executable `hcloud <Service> <Operation>`
> command and the identical payload wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- ...` for quality reporting.
> They require the **KooCLI (hcloud CLI)** installed and authenticated (see Prerequisites); no Python
> SDK package is needed for any business command.

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- <command>` — bare
> `hcloud` calls are strictly forbidden.**

### 1. Query (R3 — read-only, auto execute)

**`huawei_list_ecs_instances`** — list ECS instances and their status:

```bash
# Optional: --limit={n} --offset={n} --status={ACTIVE|SHUTOFF|ERROR|BUILD|...} --name={name} --server_id={id1,id2}
hcloud ECS ListServersDetails --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServersDetails --cli-region={region}
```

**`huawei_get_ecs_instance`** — query one instance's full detail (status, addresses, flavor, volumes, fault):

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

**`huawei_list_ecs_flavors`** — list available flavors (optionally scoped to one AZ):

```bash
# Optional: --availability_zone={az} --flavor_id={flavor_id} --limit={n} --marker={marker}
hcloud ECS ListFlavors --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region}
```

**`huawei_list_ecs_images`** — list available images (filter by OS type / architecture / status):

```bash
# Optional: --__os_type={Linux|Windows} --architecture={x86|arm} --status={active} --name={name} --limit={n}
hcloud IMS ListImages --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud IMS ListImages --cli-region={region}
```

**`huawei_list_ecs_quotas`** — query project quota usage:

```bash
hcloud ECS ShowServerLimits --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServerLimits --cli-region={region}
```

`ShowServerLimits` returns absolute limits and usage (`maxTotalInstances`/`totalInstancesUsed`,
`maxTotalCores`/`totalCoresUsed`, `maxTotalRAMSize`/`totalRamUsed`, `maxTotalKeypairs`). Note it has
**no** volume field — for disk volume quotas, additionally use:

```bash
# Required: --target_project_id={project_id} --usage=True
hcloud EVS CinderListQuotas --target_project_id={project_id} --usage=True --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS CinderListQuotas --target_project_id={project_id} --usage=True --cli-region={region}
```

### 2. Diagnose (R3 — read-only, auto execute)

**`huawei_diagnose_ecs_create_failure`** — 6-step create-failure root-cause diagnosis. Capture the
failed create request's parameters first (flavor_id, image_id, vpc_id/subnet_id, security group,
key_name, disk type/size, AZ, error message / job id from the console), then run the steps **in order**
and stop at the first failing check:

| # | Check | Command | Pass condition | Typical failure |
|---|-------|---------|----------------|-----------------|
| 1 | Quota | `hcloud ECS ShowServerLimits --cli-region={region}` | usage < limit for instances/cores/RAM | `Insufficient quota` → raise quota in console |
| 2 | Flavor | `hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}` | flavor returned; if an AZ was requested, re-check with `--availability_zone={az}` | `FlavorNotFound`/sold out → pick another flavor/AZ |
| 3 | Image | `hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active` | image exists and `active`; check `__os_type`/`architecture` matches flavor | image deleted/private mismatch → pick another image |
| 4 | Network | `hcloud VPC ListSubnets --cli-region={region}`; `hcloud VPC ListSecurityGroups/v2 --cli-region={region}`; if EIP requested `hcloud EIP ListPublicips/v2 --cli-region={region}` | subnet exists with free IPs; security group exists; EIP quota available | subnet/SG missing or no free IPs → fix network params |
| 5 | Keypair | `hcloud KPS ListKeypairs --cli-region={region}` | the `key_name` used in the request exists | `KeypairNotFound` → create keypair or drop `key_name` |
| 6 | Disk | `hcloud EVS ListVolumes --cli-region={region}`; volume quota via `hcloud EVS CinderListQuotas --cli-region={region} --target_project_id={project_id} --usage=True` (§1 has no volume field) | volume type available in the AZ, quota not exhausted | disk type unavailable → change volumetype/AZ |

The six commands in the table above run in wrapped form exactly like §1 — prefix each one with
`skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- ` (illustrated in §1 and §5).

If the failed create returned a job id (async path), check the job result:

```bash
hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
```

Report the conclusion as: **root cause (check #N) + evidence + fix suggestion**. If all 6 checks
pass, the failure is likely transient or parameter-specific — report the exact API error message
from the passed parameters and suggest retry.

**`huawei_analyze_ecs_health`** — analyze one instance's health (status / disk / network):

```bash
# Step 1 — instance status & fault
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
# Step 2 — attached volumes
hcloud ECS ListServerVolumeAttachments --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServerVolumeAttachments --cli-region={region} --server_id={server_id}
# Step 3 — volume status/size
hcloud EVS ListVolumes --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS ListVolumes --cli-region={region} --server_id={server_id}
# Step 4 — bound EIPs (security groups belong to the §2 diagnose step 4)
hcloud EIP ListPublicips/v2 --cli-region={region} --port_id.1={port_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP ListPublicips/v2 --cli-region={region} --port_id.1={port_id}
```

Health verdict: `status=ACTIVE` + volumes `available`/`in-use` + at least one NIC/EIP → healthy;
`status=ERROR`/`SHUTOFF` or a `fault` block → report the fault message and affected resource.

### 3. Manage (R2 — preview + confirm)

**`huawei_create_ecs_instance`** — create a post-paid ECS instance:

```bash
# [W] 写操作 (WRITE): creates an ECS instance — R2: preview + explicit confirmation required
# Minimal: flavor + image + name + root volume type + VPC
hcloud ECS CreatePostPaidServers --cli-region={region} --server.flavorRef={flavor_id} --server.imageRef={image_id} --server.name={instance_name} --server.root_volume.volumetype={SATA|SAS|GPSSD} --server.vpcid={vpc_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS CreatePostPaidServers --cli-region={region} --server.flavorRef={flavor_id} --server.imageRef={image_id} --server.name={instance_name} --server.root_volume.volumetype={SATA|SAS|GPSSD} --server.vpcid={vpc_id}
```

Common optional parameters (all verified via `hcloud ECS CreatePostPaidServers --help --cli-region={region}`):
`--server.availability_zone={az}`, `--server.nics.1.subnet_id={subnet_id}`,
`--server.security_groups.1.id={sg_id}`, `--server.key_name={key_name}` (mutually exclusive with
`--server.adminPass={password}`, which is never echoed back), `--server.count={n}`,
`--server.data_volumes.1.size={size_gb}`, `--server.data_volumes.1.volumetype={SATA|SAS|GPSSD}`,
`--server.publicip.eip.bandwidth.size={mbps}` + `--server.publicip.eip.bandwidth.sharetype={PER|WHOLE}`,
`--server.user_data={base64}`, and `--dry_run=true` (validates without creating).

Always run `--dry_run=true` first to validate the payload, show the result to the user, then
confirm before the real create.

**`huawei_start_ecs_instance`** — start (power on) one or more instances:

```bash
# [W] 写操作 (WRITE): starts instances — R2: preview + explicit confirmation required
hcloud ECS BatchStartServers --cli-region={region} --os-start.servers.1.id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS BatchStartServers --cli-region={region} --os-start.servers.1.id={server_id}
```

**`huawei_stop_ecs_instance`** — stop (power off) one or more instances:

```bash
# [W] 写操作 (WRITE): stops instances — R2: preview + explicit confirmation required
# --os-stop.type=SOFT (graceful, default) | HARD (forced)
hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={server_id} --os-stop.type=SOFT
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={server_id} --os-stop.type=SOFT
```

**`huawei_restart_ecs_instance`** — reboot one or more instances:

```bash
# [W] 写操作 (WRITE): reboots instances — R2: preview + explicit confirmation required
# --reboot.type=SOFT (graceful, default) | HARD (forced)
hcloud ECS BatchRebootServers --cli-region={region} --reboot.servers.1.id={server_id} --reboot.type=SOFT
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS BatchRebootServers --cli-region={region} --reboot.servers.1.id={server_id} --reboot.type=SOFT
```

### 4. Manage (R1 — preview + confirm)

**`huawei_delete_ecs_instance`** — delete one or more instances (irreversible):

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes instances — R1: verify first, then explicit confirmation
# Pre-check: hcloud ECS ShowServer --cli-region={region} --server_id={server_id}  (confirm the instance and its volumes)
hcloud ECS DeleteServers --cli-region={region} --servers.1.id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS DeleteServers --cli-region={region} --servers.1.id={server_id}
```

Optional: `--delete_publicip=true` (release bound EIP together) and `--delete_volume=true`
(delete attached volumes together). Default is `false` for both — data on volumes is preserved.
Warn the user explicitly when either flag is set.

### 5. Manage — change operations (R2/R1 — preview + confirm)

Every action below changes an **existing** instance, is preview + confirm, and is **asynchronous**
(poll the returned `job_id` per §6). Append `--cli-region={region}` to every command.

| Action | Command | Risk | Notes |
| ------ | ------- | ---- | ----- |
| `huawei_resize_ecs_instance` | `hcloud ECS ResizeServer --server_id={id} --resize.flavorRef={flavor_id}` | R2 | `--dry_run=true` first; `--resize.mode=withStopServer` allows resizing a running instance |
| `huawei_reinstall_ecs_os` | `hcloud ECS ReinstallServerWithCloudInit --server_id={id}` | R2 | keeps the current image; `--os-reinstall.adminpass` xor `--os-reinstall.keyname` |
| `huawei_reset_ecs_password` | `hcloud ECS ResetServerPassword --server_id={id} --reset-password.new_password={pwd}` | R2 | never echo the password back |
| `huawei_replace_ecs_keypair` | `hcloud ECS NovaCreateKeypair --keypair.name={name}` / `hcloud ECS NovaDeleteKeypair --keypair_name={old}` | R2 / R1 | no ECS API rebinds a keypair to a running instance — create the new key, install its public key inside the guest, then retire the old one; importing an existing public key uses `--keypair.public_key` |
| `huawei_bind_ecs_eip` | `hcloud EIP AssociatePublicips --publicip_id={eip_id} --publicip.associate_instance_type=PORT --publicip.associate_instance_id={port_id}` | R2 | service is **EIP**, not VPC |
| `huawei_unbind_ecs_eip` | `hcloud EIP DisassociatePublicips --publicip_id={eip_id}` | R1 | the instance loses public access |
| `huawei_change_ecs_security_group` | `hcloud ECS NovaAssociateSecurityGroup --server_id={id} --addSecurityGroup.name={sg_name}` / `hcloud ECS NovaDisassociateSecurityGroup --server_id={id} --removeSecurityGroup.name={sg_name}` | R2 | takes the security-group **name**, not its id; detaching may cut off management access |
| `huawei_add_ecs_nic` | `hcloud ECS BatchAddServerNics --server_id={id} --nics.1.subnet_id={subnet_id}` | R2 | also `--nics.1.ip_address`, `--nics.1.security_groups.1.id`, `--nics.1.port_id` |
| `huawei_remove_ecs_nic` | `hcloud ECS BatchDeleteServerNics --server_id={id} --nics.1.id={port_id}` | R1 | destroys the port and its private IP; a primary NIC is rejected (403) |
| `huawei_attach_ecs_volume` | `hcloud ECS AttachServerVolume --server_id={id} --volumeAttachment.volumeId={volume_id}` | R2 | `--dry_run=true`, `--volumeAttachment.device=/dev/vdb` |
| `huawei_detach_ecs_volume` | `hcloud ECS DetachServerVolume --server_id={id} --volume_id={volume_id}` | R2 | unmount inside the guest OS first; `--delete_flag=1` deletes the data disk |

Worked example — `huawei_resize_ecs_instance` (preflight → confirm → execute → poll):

```bash
# Preflight (read-only): record the current flavor, then verify the target flavor exists
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
# [W] 写操作 (WRITE): changes the instance flavor — R2: preview + `--dry_run=true` + explicit confirmation
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id} --dry_run=true
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id} --dry_run=true
```

Full per-action parameter tables, failure handling and gate wording: `references/manage-operations.md`.

### 6. Async job polling (R3 — mandatory after every write)

Every write API returns a **`job_id`** immediately and keeps working in the background. Polling that
job is part of the action:

```bash
# Step 1 — poll until status is SUCCESS or FAIL (repeat every 5-10s; give up after a bounded timeout)
hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
# Step 2 — CREATE only: poll the instance until status is ACTIVE before reporting success
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

- `SUCCESS` → report the **final** resource state; `FAIL` → report `fail_reason` + the failed
  sub-job and stop — do not blindly retry or switch to a variant command.
- A timeout means "still running" (`job_id={job_id}`), never "done".
- Skipping this step yields four specific wrong answers: "created" while the instance is still
  `BUILD`, "stopped" before the guest is powered off, "deleted" while it is still in the recycle bin,
  and no progress feedback for a multi-minute create.

## KooCLI Command Format Standard

`hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]` — 底层语法格式。

| Feature | Description | Example |
| --------- | ------------- | --------- |
| Service name | Exact KooCLI Service name beginning with uppercase/title case | `ECS`, `IMS`, `VPC`, `EVS`, `EIP`, `KPS` |
| Operation name | PascalCase | `ListServersDetails`, `ShowServer`, `CreatePostPaidServers` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--server_id=xxx` |
| Indexed parameter | `--key.N=value` | `--os-start.servers.1.id=xxx` |

## Parameter Confirmation

All parameters below were verified against `hcloud <Service> <Operation> --help` (KooCLI 7.2.12).

### Query / Diagnose operations (read-only)

| Action | Command | Key parameters |
| ------ | ------- | -------------- |
| `huawei_list_ecs_instances` | `hcloud ECS ListServersDetails --cli-region={region}` | `--limit`, `--offset`, `--status`, `--name`, `--server_id`, `--flavor`, `--ip`, `--tags`, `--enterprise_project_id` |
| `huawei_get_ecs_instance` | `hcloud ECS ShowServer --cli-region={region} --server_id={id}` | `--server_id` (required) |
| `huawei_list_ecs_flavors` | `hcloud ECS ListFlavors --cli-region={region}` | `--availability_zone`, `--flavor_id`, `--limit`, `--marker` |
| `huawei_list_ecs_images` | `hcloud IMS ListImages --cli-region={region}` | `--__os_type`, `--__platform`, `--architecture`, `--status`, `--name`, `--id`, `--min_disk`, `--min_ram`, `--limit`, `--marker` |
| `huawei_list_ecs_quotas` | `hcloud ECS ShowServerLimits --cli-region={region}` | — (project scope) |
| `huawei_diagnose_ecs_create_failure` | see Core Commands §2 | 6-step ordered checks + `hcloud ECS ShowJob --cli-region={region} --job_id={id}` |
| `huawei_analyze_ecs_health` | `ShowServer` + `ListServerVolumeAttachments` + `EVS ListVolumes --server_id` + `EIP ListPublicips/v2 --port_id` | — |

### Manage operations (write)

| Action | Command | Confirmation |
| ------ | ------- | ------------ |
| `huawei_create_ecs_instance` | `hcloud ECS CreatePostPaidServers --cli-region={region} --server.flavorRef={f} --server.imageRef={i} --server.name={n} --server.root_volume.volumetype={t} --server.vpcid={v}` | R2 — preview + `--dry_run=true` + confirm |
| `huawei_start_ecs_instance` | `hcloud ECS BatchStartServers --cli-region={region} --os-start.servers.1.id={id}` | R2 — preview + confirm |
| `huawei_stop_ecs_instance` | `hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={id} --os-stop.type=SOFT` | R2 — preview + confirm |
| `huawei_restart_ecs_instance` | `hcloud ECS BatchRebootServers --cli-region={region} --reboot.servers.1.id={id} --reboot.type=SOFT` | R2 — preview + confirm |
| `huawei_delete_ecs_instance` | `hcloud ECS DeleteServers --cli-region={region} --servers.1.id={id}` | R1 — verify + irreversible warning + confirm |

### Change operations (write)

All 11 change actions, with their required/optional parameters and risk level, are listed in
[§5 Manage — change operations](#5-manage--change-operations-r2r1--preview--confirm).
Every write action — lifecycle and change alike — is confirmed asynchronously:
`hcloud ECS ShowJob --cli-region={region} --job_id={id}`, plus `hcloud ECS ShowServer` for `create` (see §6).

## Troubleshooting

| Symptom | Likely cause | Action |
| ------- | ------------ | ------ |
| `Insufficient quota` | Project instance/volume quota exhausted | Run `huawei_list_ecs_quotas`, raise quota in console |
| `FlavorNotFound` / `Flavor ... not available` | Flavor does not exist or is sold out in the AZ | `huawei_list_ecs_flavors --availability_zone={az}` |
| Image errors (`Invalid image`, `ImageNotFound`) | Image deleted, private, or architecture mismatch | `huawei_list_ecs_images --id={id} --status=active` |
| NIC/subnet errors | Subnet missing or no free IPs | `hcloud VPC ListSubnets --cli-region={region}` + check `dhcp_enable`/CIDR usage |
| `KeypairNotFound` | `key_name` does not exist | `hcloud KPS ListKeypairs --cli-region={region}`; create keypair or remove `key_name` |
| Disk errors (`volumeType not available`) | Volume type unavailable in AZ / quota exhausted | `hcloud EVS ListVolumes --cli-region={region}`; change volumetype/AZ |
| Command fails with `--help`-verified params | Region/project mismatch or IAM scope | Check `--cli-region`, run `hcloud configure list`, review IAM policies |
| Create request rejected despite checks passing | Transient / parameter-specific error | Show the API error body; retry; check `hcloud ECS ShowJob --cli-region={region} --job_id={id}` |
| `ShowJob` returns `FAIL` | The write itself failed in the background | Report `fail_reason` + the failed sub-job as the root cause; do not retry blindly or switch to a variant command |
| Resize rejected (`Flavor ... not supported`) | Target flavor is not in the allowed resize list, or the instance state forbids resizing | Cross-check `hcloud ECS ListFlavors --flavor_id={id}` and `ShowServer`; retry with `--resize.mode=withStopServer` |

## Security Considerations

- **Credentials**: never output AK/SK, passwords, or tokens. `adminPass` is never echoed back.
- **Confirmation**: every write operation requires explicit user confirmation; never chain writes.
- **Delete safety**: `huawei_delete_ecs_instance` warns about `--delete_volume`/`--delete_publicip`
  data loss before execution.
- **Least privilege**: use the policies in `references/iam-policies.md`; do not grant
  `ECS FullAccess` when read-only diagnosis is enough.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/manage-operations.md` — Per-action parameter tables, gates and failure handling for resize / reinstall / password / keypair / EIP / security group / NIC / volume changes, plus the async-job polling contract
- `references/sdk-examples.md` — Python and Java SDK examples for create / start / stop / restart / delete, and a worked create-failure troubleshooting example
- `references/related-skills.md` — Capability boundaries and how to hand an out-of-scope request (e.g. RDS) back to the user
- `references/cli-installation-guide.md` — CLI installation and configuration
- `references/verification-method.md` — Verification method details
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/dataflow-diagram.md` — Mermaid data flow diagram