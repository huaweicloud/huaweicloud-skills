---
name: huawei-cloud-ecs-manage
description: |
  Use when managing Huawei Cloud ECS (Elastic Cloud Server / 弹性云服务器) instances —
  lifecycle management (create / start / stop / restart / delete), tag-based batch start / stop /
  reboot, batch tag management, yearly-monthly (prePaid) and spot (竞价) creation, batch
  heterogeneous creation, day-to-day change operations (resize / reinstall OS / reset password /
  replace keypair / bind & unbind EIP / change security group / add & remove NIC / attach & detach
  volume / migrate enterprise project), instance querying, quota/flavor/image inspection, VNC
  console access, mandatory async-job polling after every write, and multi-step root-cause
  diagnosis of ECS instance creation failures (IAM → balance → quota → flavor → image → network →
  keypair → disk). Monitoring metrics are handed off to the dedicated ECS monitoring skill.
  Provides 31 huawei_* actions: huawei_list_ecs_instances, huawei_get_ecs_instance, huawei_list_ecs_flavors,
  huawei_list_ecs_images, huawei_list_ecs_quotas, huawei_diagnose_ecs_create_failure, huawei_analyze_ecs_health,
  huawei_create_ecs_instance, huawei_batch_create_ecs_instances, huawei_start_ecs_instance, huawei_stop_ecs_instance,
  huawei_restart_ecs_instance, huawei_batch_start_ecs_by_tag, huawei_batch_stop_ecs_by_tag, huawei_batch_reboot_ecs_by_tag,
  huawei_batch_tag_ecs, huawei_batch_untag_ecs, huawei_get_ecs_vnc_console, huawei_change_ecs_enterprise_project,
  huawei_delete_ecs_instance, huawei_resize_ecs_instance, huawei_reinstall_ecs_os, huawei_reset_ecs_password,
  huawei_replace_ecs_keypair, huawei_bind_ecs_eip, huawei_unbind_ecs_eip, huawei_change_ecs_security_group,
  huawei_add_ecs_nic, huawei_remove_ecs_nic, huawei_attach_ecs_volume, huawei_detach_ecs_volume.
  Service keywords: ECS, elastic cloud server, instance, VM, server, flavor, image, quota,
  keypair, security group, subnet, EIP, job, resize, reinstall, tag, batch, VNC, enterprise project,
  prePaid, spot, 云服务器, 弹性云服务器, 实例, 规格, 镜像, 配额, 密钥对, 安全组, 子网, 创建失败,
  启动, 停止, 重启, 删除, 变更规格, 重装系统, 重置密码, 绑定EIP, 解绑EIP, 网卡, 挂载磁盘, 卸载磁盘,
  标签, 批量启停, 批量打标签, 包年包月, 竞价实例, 企业项目, 监控指标, 异步任务.
  Triggers include: "ECS 创建失败", "云服务器创建失败", "创建云主机失败", "ECS 创建不了",
  "create ECS failed", "instance creation failed", "创建云服务器", "启动/停止/重启/删除云服务器",
  "ECS 规格", "ECS 配额", "ECS 镜像", "list ECS instances", "diagnose ECS", "ECS health",
  "ECS 变更规格", "云服务器升配", "ECS 重装系统", "重置云服务器密码", "更换密钥对",
  "绑定弹性公网IP", "解绑EIP", "更换安全组", "添加网卡", "删除网卡", "挂载云硬盘", "卸载云硬盘",
  "ECS resize", "reinstall ECS OS", "按标签批量启停", "批量重启云服务器", "批量打标签",
  "批量删除标签", "包年包月创建ECS", "竞价实例", "spot instance", "ECS VNC 控制台", "VNC 地址",
  "ECS 迁移企业项目", "ECS 监控指标", "async job polling".
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

> **Run this step first**: quality reporting depends on `skill-quality-cli`, ensured idempotently
> by `scripts/ensure_cli.sh` (installs once if missing, skips if present; **no auto-upgrade** —
> run `skill-quality-cli upgrade` manually). Offline failure degrades silently; re-run once online.
> Always run `hcloud ECS <Operation> --help` before constructing a command.

## Overview

This skill provides AI Agent capabilities for Huawei Cloud ECS: lifecycle management, tag-based
batch operations, tag management, querying, VNC console access, enterprise-project migration, and an
**8-step create-failure diagnosis** ordered **IAM → balance → quota → flavor → image → network →
keypair → disk**. It exposes 31 `huawei_*` actions:

| Capability | Risk | Actions |
| ---------- | ---- | ------- |
| Query (read-only) | R3 | `huawei_list_ecs_instances`, `huawei_get_ecs_instance`, `huawei_list_ecs_flavors`, `huawei_list_ecs_images`, `huawei_list_ecs_quotas` |
| Diagnose (read-only) | R3 | `huawei_diagnose_ecs_create_failure`, `huawei_analyze_ecs_health` |
| Lifecycle | R2 | `huawei_create_ecs_instance`, `huawei_batch_create_ecs_instances`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`, `huawei_restart_ecs_instance` |
| Batch by tag | R2 | `huawei_batch_start_ecs_by_tag`, `huawei_batch_stop_ecs_by_tag`, `huawei_batch_reboot_ecs_by_tag` |
| Tags | R2 | `huawei_batch_tag_ecs`, `huawei_batch_untag_ecs` |
| Ops assist | R3 / R2 | `huawei_get_ecs_vnc_console` (R3), `huawei_change_ecs_enterprise_project` (R2) |
| Lifecycle | R1 | `huawei_delete_ecs_instance` |
| Change ops (§5) | R2 | `huawei_resize_ecs_instance`, `huawei_reinstall_ecs_os`, `huawei_reset_ecs_password`, `huawei_replace_ecs_keypair`, `huawei_bind_ecs_eip`, `huawei_change_ecs_security_group`, `huawei_add_ecs_nic`, `huawei_attach_ecs_volume`, `huawei_detach_ecs_volume` |
| Change ops (§5) | R1 | `huawei_unbind_ecs_eip`, `huawei_remove_ecs_nic` |

Every write is **asynchronous**: polling the returned `job_id` is a **mandatory** post-step —
see [§6 Async job polling](#6-async-job-polling-r3--mandatory-after-every-write).

**Scope boundaries:**

- ✅ Query instances/flavors/images/quotas; diagnose create failures and instance health
- ✅ Create post-paid / yearly-monthly / spot and batch heterogeneous instances; start/stop/restart/
  delete; tag-based batch start/stop/reboot; batch tag/untag; VNC console; enterprise-project migration
- ✅ Change an **existing instance**: resize, reinstall OS, reset password, replace keypair,
  bind/unbind EIP, attach/detach security group, add/remove NIC, attach/detach volume
- ✅ Read and point to CES metrics; hand deep monitoring work to the dedicated ECS monitoring skill
- ❌ NEVER create, delete or reconfigure the VPC / subnet / security-group **resource** or the
  EVS **volume resource** itself — only attach/detach existing resources
- ❌ NEVER execute a write without explicit confirmation (batch preview + count, > 50 → second confirm)
- ❌ NEVER report a write as "done" before its async job reaches `SUCCESS` and, for `create`,
  before the instance reaches `ACTIVE`
- ❌ NEVER echo credentials (AK/SK, passwords, tokens, VNC URLs, private keys)
- ❌ NEVER auto-purchase a paid resource: `prePaid` / `spot` creation stays preview + confirm
- ➡️ Out of scope: **RDS / database** queries (hand back to the user, see `references/related-skills.md`)

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli`
(installed by `scripts/ensure_cli.sh` if absent).

## Critical Warnings

| Trap | Why |
| ---- | --- |
| IAM permission is the #1 non-quota create blocker | `403` / `not authorized` / `APIGW.0301` means the action is missing from the user's policy — check `references/iam-policies.md`, never widen to `ECS FullAccess` |
| Account balance / arrears blocks paid create | `Insufficient account balance` / `Account is in arrears` / `Order payment failed` — check BSS balance first for `prePaid` and for orders with `isAutoPay=true` |
| Quota exhaustion is the #1 quota create failure | `Insufficient quota` / `Quota exceeded` — check `ShowServerLimits` first |
| Flavor must exist **in the target region/AZ** | Filter `ListFlavors` by `--availability_zone`; a sold-out flavor fails |
| Image must be `active` and match the flavor architecture | Deleted/private image or x86/ARM mismatch fails provisioning |
| Subnet with no free IPs blocks create | An exhausted CIDR or `dhcp` disabled fails NIC allocation |
| Security group must exist before create | Non-existent SG ID fails the request |
| Keypair errors are misleading | `key_name` that does not exist → `KeypairNotFound`; verify with `KPS ListKeypairs` |
| Disk/AZ availability | Volume types (SAS/GPSSD/SSD/GPSSD2/ESSD2…) may be unavailable in the AZ |
| Tag filter matches too many instances | Batch by tag previews the resolved list; > 50 targets needs a second confirmation |
| Security group **name** may be ambiguous | Pass the SG **UUID** to `--addSecurityGroup.name` (accepts UUID or name); resolve a name via `VPC ListSecurityGroups/v2` and reject on duplicates |
| Deletion is irreversible | R1: verify the instance, confirm no data dependency, then require explicit confirmation |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated — see
   `references/cli-installation-guide.md`. Modes: AK/SK env vars (`HUAWEICLOUD_SDK_AK`/`_SK`,
   `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY`) or a local profile (`hcloud configure list`, mode `AKSK`).
2. **Region**: ECS is regional. Always pass `--cli-region={region}` (e.g. `cn-north-4`).
3. **IAM permissions**: least-privilege policies in `references/iam-policies.md`. Query/diagnose:
   `ecs:cloudServers:list|get`, `ecs:cloudServerFlavors:list`, `ecs:cloudServerImages:list`,
   `ecs:jobs:get`, `ecs:serverVolumes:list`, `ims:images:list`, `vpc:subnets:list`,
   `vpc:securityGroups:list`, `vpc:publicIps:list`, `evs:volumes:list`, `kps:keypairs:list`.
   Manage: `ecs:cloudServers:create|action|delete`, `ecs:serverTags:create|delete|list`,
   `ecs:cloudServers:remoteConsole`, `eps:resources:migrate`, plus `bss:balance:view` (or the
   BSS balance API) for the balance check.
4. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent); upgrade with
   `skill-quality-cli upgrade`; disable telemetry with `SKILL_QUALITY_REPORT=0`.

## Workflow

```
1. Identify target → region, instance_id(s) / tag filter / flavor_id / image_id / vpc_id /
   subnet_id / key_name / enterprise_project_id, intent keywords
2. Classify intent →
     - Query/Diagnose/VNC/CES entry (R3): auto
     - Lifecycle (R2): create / batch-create / start / stop / restart — preview + confirm
     - Batch by tag (R2): resolve tag → preview list + count → confirm → execute per id
     - Tags (R2): preview target list + tag key/value → confirm → execute per id
     - Delete (R1): show details, irreversible warning, explicit confirmation
     - Change ops (R2/R1): current state + preview + confirm
3. Preflight → read-only checks first; for create verify IAM and, for paid modes, the balance
4. Execute → build the hcloud command from the verified templates below
5. Capture the job id → then poll `ECS ShowJob` until `SUCCESS|FAIL`; create ALSO polls
   `ECS ShowServer` until `ACTIVE`; batch loops aggregate per-instance results
6. Output → structured JSON summary + readable diagnosis report; quality via skill-quality-cli
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (create, batch, tags, change ops): show the full command, targets and expected end
  state, then ask "confirm?"; paid creation (`prePaid`/`spot`/`isAutoPay`) also states billing mode, period and cost.
- **Batch operations**: print the resolved target list (id + name + status) and count; **> 50**
  requires a second confirmation. Execute per id and aggregate
  `{success[], failed[{id, error_code, error_msg}]}` without aborting on one failure.
- **R1 actions** (`delete`, `unbind EIP`, `remove NIC`): read-only check first, state the
  irreversible / connectivity impact, then require explicit confirmation. For
  `huawei_detach_ecs_volume` (R2) warn that `--delete_flag=1` deletes the data disk.
- **Security-group change**: pass the SG **UUID** via `--addSecurityGroup.name`; a name input is
  resolved via `VPC ListSecurityGroups/v2` first and **rejected when duplicated**.
- **Async polling is mandatory**: a `job_id` without polling is an **incomplete** action, not a
  success. Write blocks below are marked `[W]` / 写操作 (verb keywords: create / start / stop /
  restart / delete / tag / migrate — the same verbs the test pipeline keys on).

## Core Commands

> Commands are shown in **dual form**: the bare `hcloud <Service> <Operation>` and the identical
> payload wrapped with `skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- ...`.
> **⚠️ Mandatory: every `hcloud` call MUST be wrapped — bare `hcloud` calls are forbidden.**

### 1. Query (R3 — read-only, auto execute)

**`huawei_list_ecs_instances`** — list instances and their status/tags:

```bash
# Optional: --limit --offset --status={ACTIVE|SHUTOFF|ERROR|BUILD} --name --server_id={id1,id2}
# Optional tag filter: --tags={key}={value}[,{key}={value}]  (also used to resolve batch targets)
hcloud ECS ListServersDetails --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServersDetails --cli-region={region}
```

**`huawei_get_ecs_instance`** — one instance's full detail (status, addresses, flavor, volumes, fault):

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

**`huawei_list_ecs_flavors`** / **`huawei_list_ecs_images`** / **`huawei_list_ecs_quotas`**:

```bash
# Optional: --availability_zone --flavor_id --limit --marker
hcloud ECS ListFlavors --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region}
# Optional: --__os_type={Linux|Windows} --architecture={x86|arm} --status=active --name --id --limit
hcloud IMS ListImages --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud IMS ListImages --cli-region={region}
hcloud ECS ShowServerLimits --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServerLimits --cli-region={region}
# Disk quota (ShowServerLimits has no volume field):
hcloud EVS CinderListQuotas --target_project_id={project_id} --usage=True --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS CinderListQuotas --target_project_id={project_id} --usage=True --cli-region={region}
```

### 2. Diagnose (R3 — read-only, auto execute)

**`huawei_diagnose_ecs_create_failure`** — 8-step root-cause diagnosis. Capture the failed
request's parameters first, then run the steps **in order** and stop at the first failing check:

| # | Check | Command | Pass condition / typical failure |
|---|-------|---------|----------------------------------|
| 1 | IAM | Re-run the smallest read (`ECS ShowServerLimits`, or the failed call) | `403` / `not authorized` → missing action, fix per `references/iam-policies.md`; never widen to FullAccess |
| 2 | Balance | BSS balance API/SDK or console (KooCLI has **no** BSS service) | `Insufficient account balance` / `Account is in arrears` / `Order payment failed` → recharge before retrying paid create |
| 3 | Quota | `hcloud ECS ShowServerLimits --cli-region={region}` | usage < limit for instances/cores/RAM; `Insufficient quota` → raise quota |
| 4 | Flavor | `hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}` | flavor returned in the AZ; `FlavorNotFound`/sold out → pick another flavor/AZ |
| 5 | Image | `hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active` | image `active` and architecture matches the flavor |
| 6 | Network | `hcloud VPC ListSubnets --cli-region={region}`; `hcloud VPC ListSecurityGroups/v2 --cli-region={region}`; `hcloud EIP ListPublicips/v2 --cli-region={region}` | subnet has free IPs, SG exists, EIP quota available |
| 7 | Keypair | `hcloud KPS ListKeypairs --cli-region={region}` | the `key_name` exists; `KeypairNotFound` → create it or drop `key_name` |
| 8 | Disk | `hcloud EVS ListVolumes --cli-region={region}`; volume quota (§1) | volume type available in the AZ, quota not exhausted |

Every command in the table is wrapped like §1 (`skill-quality-cli run --skill-name
huawei-cloud-ecs-manage -- `). If the failed create returned a job id, also check
`hcloud ECS ShowJob --cli-region={region} --job_id={job_id}`.

Report the conclusion as **root cause (check #N) + evidence + fix suggestion**. Distinguish
plainly: `403/not authorized` = **IAM permission**, `Insufficient account balance/arrears` =
**account balance**, `Insufficient quota` = **quota**. If all checks pass, report the exact API
error and suggest a retry.

**`huawei_analyze_ecs_health`** — status / disk / network:

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
hcloud ECS ListServerVolumeAttachments --cli-region={region} --server_id={server_id}
hcloud EVS ListVolumes --cli-region={region} --server_id={server_id}
hcloud EIP ListPublicips/v2 --cli-region={region} --port_id.1={port_id}
```

Prefix each with the quality wrapper. Verdict: `ACTIVE` + volumes `available`/`in-use` + at least
one NIC/EIP → healthy; `ERROR`/`SHUTOFF` or a `fault` block → report the fault. For CPU/memory/
disk/network metrics use the **CES entry** below or the dedicated ECS monitoring skill
(`references/related-skills.md`):

```bash
# Metrics entry (R3): list available SYS.ECS metrics, then read one series
hcloud CES ListMetrics --cli-region={region} --namespace=SYS.ECS --dim.0=instance_id,{server_id}
hcloud CES ShowMetricData --cli-region={region} --namespace=SYS.ECS --metric_name=cpu_util --dim.0=instance_id,{server_id} --filter=average --period=300 --from={start_ms} --to={end_ms}
```

### 3. Manage — create, batch, tags, VNC, enterprise project (R2/R3)

**`huawei_create_ecs_instance`** — post-paid (`CreatePostPaidServers`) or yearly-monthly / spot
(`CreateServers`, V1.1):

```bash
# [W] 写操作 (WRITE): creates an ECS instance — R2: preview + explicit confirmation required
hcloud ECS CreatePostPaidServers --cli-region={region} --server.flavorRef={flavor_id} --server.imageRef={image_id} --server.name={instance_name} --server.root_volume.volumetype={SAS} --server.vpcid={vpc_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS CreatePostPaidServers --cli-region={region} --server.flavorRef={flavor_id} --server.imageRef={image_id} --server.name={instance_name} --server.root_volume.volumetype={SAS} --server.vpcid={vpc_id}
```

Billing / market extensions (all verified with `hcloud ECS CreateServers --help`):

| Mode | Parameters |
| ---- | ---------- |
| Post-paid | `--server.extendparam.chargingMode=postPaid` (default) |
| Yearly/monthly | `--server.extendparam.chargingMode=prePaid --server.extendparam.periodType={month\|year} --server.extendparam.periodNum={n}`; add `--server.extendparam.isAutoPay={true\|false}` and optionally `--server.extendparam.isAutoRenew` |
| Spot | `--server.extendparam.chargingMode=postPaid --server.extendparam.marketType=spot [--server.extendparam.spotPrice={price}] [--server.extendparam.interruption_policy=immediate]` |
| Enterprise project | `--server.extendparam.enterprise_project_id={eps_id}` |
| Batch heterogeneous | `--server.count={n}` for a homogeneous batch; for **different flavors/networks** create one group at a time (per flavor/subnet) and aggregate the resulting server ids |

`prePaid` with `--server.key_name` also requires `op_svc_userid` metadata (see the `--help` note);
`isAutoPay=true` is the point where balance matters. Always run `--dry_run=true` first, show the
result (billing mode, period, count, cost warning), confirm, then execute and poll §6.

**`huawei_batch_create_ecs_instances`** — batch heterogeneous creation: render one preview block per
`{flavor, image, subnet, count}` group, confirm the whole plan, execute group by group, and return
`{groups[], servers[{group, server_id, job_id, status}]}`.

**`huawei_batch_start_ecs_by_tag` / `huawei_batch_stop_ecs_by_tag` / `huawei_batch_reboot_ecs_by_tag`**
— resolve tag → preview → per-id execute → aggregate:

```bash
# Step 1 (R3): resolve the targets
hcloud ECS ListServersDetails --cli-region={region} --tags={key}={value} --limit=100
# Step 2 (R2): preview the id/name/status list + count; > 50 targets needs a second confirmation
# Step 3: loop per id so one failure cannot abort the batch, then poll each job (§6)
# [W] 写操作 (WRITE): starts the tagged instance — R2: preview + confirmation per batch
hcloud ECS BatchStartServers --cli-region={region} --os-start.servers.1.id={server_id}
hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={server_id} --os-stop.type=SOFT
hcloud ECS BatchRebootServers --cli-region={region} --reboot.servers.1.id={server_id} --reboot.type=SOFT
```

Aggregate `{success[{id, job_id, status}], failed[{id, error_code, error_msg}]}`; continue after a
failure and report both lists. Paginate the tag query (`--limit`/`--marker`) so the preview covers
**all** matching instances, not just the first page.

**`huawei_batch_tag_ecs` / `huawei_batch_untag_ecs`** — target by instance-id list or query
condition (`--server_id`, `--tags`, `--name`, `--status`):

```bash
# [W] 写操作 (WRITE): adds tags to one instance — R2: preview target list + tags, then confirm
hcloud ECS BatchCreateServerTags --cli-region={region} --server_id={server_id} --action=create --tags.1.key={key} --tags.1.value={value}
# [W] 写操作 (WRITE): deletes tags from one instance — R2: preview target list + tags, then confirm
hcloud ECS BatchDeleteServerTags --cli-region={region} --server_id={server_id} --action=delete --tags.1.key={key}
```

The tag API is per-instance, so resolve the target set first and loop per id with the same
success/failed aggregation. Read tags with `hcloud ECS ListServerTags --cli-region={region}`.

**`huawei_get_ecs_vnc_console`** (R3) — temporary noVNC address; **validity is short (about
10 minutes, platform-controlled), re-obtain when expired**, and never print/reuse it as a
permanent link:

```bash
hcloud ECS ShowServerRemoteConsole --cli-region={region} --server_id={server_id} --remote_console.protocol=vnc --remote_console.type=novnc
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServerRemoteConsole --cli-region={region} --server_id={server_id} --remote_console.protocol=vnc --remote_console.type=novnc
```

**`huawei_change_ecs_enterprise_project`** (R2) — migrate an instance (and optionally associated
EVS/EIP) to another enterprise project. Pre-check the current/target EP and resolve the resource
type mapping, then confirm:

```bash
hcloud EPS ListEnterpriseProject --cli-region={region}
hcloud EPS ListResourceMapping --cli-region={region}
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
# [W] 写操作 (WRITE): migrates the ECS to another enterprise project (billing attribution changes) — R2: preview + explicit confirmation required
hcloud EPS MigrateResource --cli-region={region} --enterprise_project_id={target_eps_id} --resource_id={server_id} --resource_type={resource_type} --project_id={project_id} [--associated=true]
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EPS MigrateResource --cli-region={region} --enterprise_project_id={target_eps_id} --resource_id={server_id} --resource_type={resource_type} --project_id={project_id}
```

Verify afterwards with `ECS ShowServer` / `ListServersDetails --enterprise_project_id={target_eps_id}`.
`--associated=true` migrates ECS-associated EVS disks and EIPs too.

**`huawei_start_ecs_instance` / `huawei_stop_ecs_instance` / `huawei_restart_ecs_instance`**:

```bash
# [W] 写操作 (WRITE) — R2: preview + explicit confirmation required
hcloud ECS BatchStartServers --cli-region={region} --os-start.servers.1.id={server_id}
hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={server_id} --os-stop.type=SOFT
hcloud ECS BatchRebootServers --cli-region={region} --reboot.servers.1.id={server_id} --reboot.type=SOFT
```

`--os-stop.type` / `--reboot.type`: `SOFT` (graceful, default) | `HARD` (forced). Prefix each with
the quality wrapper.

### 4. Manage (R1 — preview + confirm)

**`huawei_delete_ecs_instance`** — delete one or more instances (irreversible):

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes instances — R1: verify first, then explicit confirmation
# Pre-check: hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
hcloud ECS DeleteServers --cli-region={region} --servers.1.id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS DeleteServers --cli-region={region} --servers.1.id={server_id}
```

Optional `--delete_publicip=true` (release bound EIP) and `--delete_volume=true` (delete attached
volumes); both default to `false` — warn explicitly when set.

### 5. Manage — change operations (R2/R1 — preview + confirm)

Every action below changes an **existing** instance, is preview + confirm, and is **asynchronous**
(poll `job_id` per §6). Append `--cli-region={region}`.

| Action | Command | Risk | Notes |
| ------ | ------- | ---- | ----- |
| `huawei_resize_ecs_instance` | `hcloud ECS ResizeServer --server_id={id} --resize.flavorRef={flavor_id}` | R2 | `--dry_run=true` first; `--resize.mode=withStopServer` for running instances |
| `huawei_reinstall_ecs_os` | `hcloud ECS ReinstallServerWithCloudInit --server_id={id}` | R2 | keeps the current image; `--os-reinstall.adminpass` xor `--os-reinstall.keyname` |
| `huawei_reset_ecs_password` | `hcloud ECS ResetServerPassword --server_id={id} --reset-password.new_password={pwd}` | R2 | never echo the password |
| `huawei_replace_ecs_keypair` | `hcloud ECS NovaCreateKeypair --keypair.name={name}` / `hcloud ECS NovaDeleteKeypair --keypair_name={old}` | R2 / R1 | no ECS API rebinds a keypair to a running instance — create the key, install its public key in the guest, then retire the old one; importing a public key uses `--keypair.public_key` |
| `huawei_bind_ecs_eip` | `hcloud EIP AssociatePublicips --publicip_id={eip_id} --publicip.associate_instance_type=PORT --publicip.associate_instance_id={port_id}` | R2 | service is **EIP**, not VPC |
| `huawei_unbind_ecs_eip` | `hcloud EIP DisassociatePublicips --publicip_id={eip_id}` | R1 | the instance loses public access |
| `huawei_change_ecs_security_group` | `hcloud ECS NovaAssociateSecurityGroup --server_id={id} --addSecurityGroup.name={sg_id_or_name}` / `NovaDisassociateSecurityGroup --server_id={id} --removeSecurityGroup.name={sg_id_or_name}` | R2 | **ID first**: the field accepts a UUID or name; name inputs resolved with `VPC ListSecurityGroups/v2`, **duplicate → reject**; detaching may cut management access |
| `huawei_add_ecs_nic` | `hcloud ECS BatchAddServerNics --server_id={id} --nics.1.subnet_id={subnet_id}` | R2 | also `--nics.1.ip_address`, `--nics.1.security_groups.1.id`, `--nics.1.port_id` |
| `huawei_remove_ecs_nic` | `hcloud ECS BatchDeleteServerNics --server_id={id} --nics.1.id={port_id}` | R1 | destroys the port/private IP; the primary NIC returns 403 |
| `huawei_attach_ecs_volume` | `hcloud ECS AttachServerVolume --server_id={id} --volumeAttachment.volumeId={volume_id}` | R2 | `--dry_run=true`; `--volumeAttachment.device=/dev/vdb` |
| `huawei_detach_ecs_volume` | `hcloud ECS DetachServerVolume --server_id={id} --volume_id={volume_id}` | R2 | unmount in-guest first; `--delete_flag=1` deletes the data disk |

Security-group name resolution (MUST run before a name-based change):

```bash
# R3: find the group(s) by name; exactly one match → use its id/name, zero → stop, ≥2 → reject
hcloud VPC ListSecurityGroups/v2 --cli-region={region} --limit=100
```

Worked example — `huawei_resize_ecs_instance` (preflight → confirm → execute → poll):

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
# [W] 写操作 (WRITE): changes the instance flavor — R2: `--dry_run=true` + explicit confirmation
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id} --dry_run=true
```

Full per-action parameter tables, batch/tag/VNC/EP details and failure handling:
`references/manage-operations.md`.

### 6. Async job polling (R3 — mandatory after every write)

Every write returns a **`job_id`** immediately; polling is part of the action:

```bash
hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
# CREATE only: poll until status is ACTIVE before reporting success
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

- `SUCCESS` → report the **final** state; `FAIL` → report `fail_reason` + the failed sub-job, stop.
- A timeout means "still running (`job_id=…`)", never "done".
- Batch loops poll every returned job and report per-instance results; one failure never aborts the
  remaining targets.

## KooCLI Command Format Standard

`hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]` — 底层语法格式。

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | Exact KooCLI Service name in title case | `ECS`, `IMS`, `VPC`, `EVS`, `EIP`, `KPS`, `EPS`, `CES` |
| Operation name | PascalCase | `ListServersDetails`, `BatchCreateServerTags`, `ShowServerRemoteConsole` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--server_id=xxx` |
| Indexed parameter | `--key.N=value` | `--os-start.servers.1.id=xxx` |

## Parameter Confirmation

All parameters below were verified against `hcloud <Service> <Operation> --help` (KooCLI 7.3.12).

### Query / Diagnose / Ops-assist

| Action | Command | Key parameters |
| ------ | ------- | -------------- |
| `huawei_list_ecs_instances` | `hcloud ECS ListServersDetails` | `--limit`, `--offset`, `--status`, `--name`, `--server_id`, `--flavor`, `--ip`, `--tags`, `--enterprise_project_id` |
| `huawei_get_ecs_instance` | `hcloud ECS ShowServer --server_id` | `--server_id` (required) |
| `huawei_list_ecs_flavors` | `hcloud ECS ListFlavors` | `--availability_zone`, `--flavor_id`, `--limit`, `--marker` |
| `huawei_list_ecs_images` | `hcloud IMS ListImages` | `--__os_type`, `--architecture`, `--status`, `--name`, `--id`, `--limit` |
| `huawei_list_ecs_quotas` | `hcloud ECS ShowServerLimits` | — (project scope); disk quota via `EVS CinderListQuotas` |
| `huawei_diagnose_ecs_create_failure` | see §2 | 8 ordered checks incl. IAM + balance |
| `huawei_analyze_ecs_health` | see §2 | `ShowServer` + attachments + EVS + EIP + CES entry |
| `huawei_get_ecs_vnc_console` | `hcloud ECS ShowServerRemoteConsole` | `--server_id`, `--remote_console.protocol=vnc`, `--remote_console.type=novnc` |

### Manage operations (write)

| Action | Command | Confirmation |
| ------ | ------- | ------------ |
| `huawei_create_ecs_instance` | `CreatePostPaidServers` / `CreateServers` (+ extendparam billing) | R2 — preview + `--dry_run=true` + cost warning + confirm |
| `huawei_batch_create_ecs_instances` | one `CreateServers` group per flavor/subnet, `--server.count` | R2 — group plan preview + confirm |
| `huawei_batch_start_ecs_by_tag` / `_stop_` / `_reboot_` | `ListServersDetails --tags` → per-id `Batch*Servers` | R2 — target list + count (> 50 second confirm) |
| `huawei_batch_tag_ecs` / `huawei_batch_untag_ecs` | `BatchCreateServerTags --action=create` / `BatchDeleteServerTags --action=delete` | R2 — target list + tags preview |
| `huawei_start_ecs_instance` / `_stop_` / `_restart_` | `BatchStartServers` / `BatchStopServers` / `BatchRebootServers` | R2 — preview + confirm |
| `huawei_change_ecs_enterprise_project` | `EPS MigrateResource` | R2 — current/target EP + billing impact |
| `huawei_delete_ecs_instance` | `DeleteServers` | R1 — verify + irreversible warning + confirm |

### Change operations (write)

All 11 change actions, with required/optional parameters and risk, are in
[§5 Manage — change operations](#5-manage--change-operations-r2r1--preview--confirm).
Every write — lifecycle, batch, change alike — is confirmed asynchronously:
`hcloud ECS ShowJob --cli-region={region} --job_id={id}`, plus `ShowServer` for create (§6).

## Troubleshooting

| Symptom | Likely cause | Action |
| ------- | ------------ | ------ |
| `403` / `not authorized` / `APIGW.0301` | Missing IAM action (not a credentials error when other reads work) | Check `references/iam-policies.md`; grant the specific action; do not widen to FullAccess |
| `Insufficient account balance` / `Account is in arrears` / `Order payment failed` | Account balance/arrears blocks a paid create or `isAutoPay` order | Recharge via the Billing Center; confirm balance before retrying |
| `Insufficient quota` | Instance/volume quota exhausted | `huawei_list_ecs_quotas`, raise quota |
| `FlavorNotFound` / sold out | Flavor unavailable in the AZ | `huawei_list_ecs_flavors --availability_zone={az}` |
| Image errors | Deleted/private/wrong architecture | `huawei_list_ecs_images --id={id} --status=active` |
| NIC/subnet errors | Subnet missing or no free IPs | `VPC ListSubnets` + check `dhcp_enable`/CIDR usage |
| `KeypairNotFound` | `key_name` does not exist | `KPS ListKeypairs`; create it or remove `key_name` |
| Security-group change rejected / wrong group attached | Duplicate SG name or name/ID mix-up | Resolve by `VPC ListSecurityGroups/v2`; duplicate → ask for the UUID; prefer the UUID as the `name` value |
| Batch request fails on one id | The batch API rejects a mixed/invalid set | Execute per id, aggregate success/failed, retry only failed ids |
| Tag batch matched unexpected instances | Tag scope too broad / stale preview | Re-run the tag query, show the full resolved list and count, re-confirm |
| `ShowJob` returns `FAIL` | The write failed in the background | Report `fail_reason` + failed sub-job; do not retry blindly |
| Resize rejected | Target flavor not in the resize list / state forbids it | Cross-check `ListFlavors` + `ShowServer`; retry with `--resize.mode=withStopServer` |

## Security Considerations

- **Credentials**: never output AK/SK, passwords, tokens, VNC URLs or private keys.
- **Confirmation**: every write requires explicit confirmation; never chain writes.
- **Paid resources**: `prePaid` / `spot` creation always states billing mode, period and cost and
  requires confirmation; never purchase automatically.
- **Batch safety**: show the target list and count, second-confirm over 50 instances, and never
  widen a tag filter silently.
- **Delete safety**: `huawei_delete_ecs_instance` warns about `--delete_volume`/`--delete_publicip`.
- **Least privilege**: use `references/iam-policies.md`; do not grant `ECS FullAccess` for diagnosis.

## Reference Documents

- `references/cli-installation-guide.md` — CLI installation (KooCLI 7.2.x) and both authentication modes
- `references/iam-policies.md` — least-privilege policies and the create-failure IAM precheck
- `references/verification-method.md` — verification method: static checks, live read-only runs, offline gates
- `references/manage-operations.md` — per-action tables, gates, batch/tag/VNC/enterprise-project/billing sections, async-job polling
- `references/related-skills.md` — capability boundaries, monitoring/VPC/EVS/RDS entries, one cross-skill orchestration path
- `references/sdk-examples.md` — Python/Java SDK examples (create incl. prePaid/spot, batch, lifecycle)
- `references/acceptance-criteria.md`, `references/dataflow-diagram.md` — acceptance criteria and data-flow diagram