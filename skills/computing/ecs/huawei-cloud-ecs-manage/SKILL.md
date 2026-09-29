---
name: huawei-cloud-ecs-manage
description: |
  Use when managing Huawei Cloud ECS (Elastic Cloud Server / 弹性云服务器) instances —
  lifecycle management (create / start / stop / restart / delete), instance querying,
  quota/flavor/image inspection, and multi-step root-cause diagnosis of ECS instance
  creation failures (quota → flavor → image → network → keypair → disk).
  Provides 12 huawei_* actions: huawei_list_ecs_instances, huawei_get_ecs_instance,
  huawei_list_ecs_flavors, huawei_list_ecs_images, huawei_list_ecs_quotas,
  huawei_diagnose_ecs_create_failure, huawei_analyze_ecs_health, huawei_create_ecs_instance,
  huawei_start_ecs_instance, huawei_stop_ecs_instance, huawei_restart_ecs_instance,
  huawei_delete_ecs_instance.
  Service keywords: ECS, elastic cloud server, instance, VM, server, flavor, image, quota,
  keypair, security group, subnet, EIP, 云服务器, 弹性云服务器, 实例, 规格, 镜像, 配额,
  密钥对, 安全组, 子网, 创建失败, 启动, 停止, 重启, 删除.
  Triggers include: "ECS 创建失败", "云服务器创建失败", "创建云主机失败", "ECS 创建不了",
  "create ECS failed", "instance creation failed", "创建云服务器", "启动云服务器",
  "停止云服务器", "重启云服务器", "删除云服务器", "ECS 规格", "ECS 配额", "ECS 镜像",
  "list ECS instances", "diagnose ECS", "ECS health", "ecs create diagnose".
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

It exposes 12 `huawei_*` actions in four capability groups:

| Capability | Risk level | Actions |
| ---------- | ---------- | ------- |
| Query (read-only) | R3 — auto execute | `huawei_list_ecs_instances`, `huawei_get_ecs_instance`, `huawei_list_ecs_flavors`, `huawei_list_ecs_images`, `huawei_list_ecs_quotas` |
| Diagnose (read-only) | R3 — auto execute | `huawei_diagnose_ecs_create_failure`, `huawei_analyze_ecs_health` |
| Manage | R2 — preview + confirm | `huawei_create_ecs_instance`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`, `huawei_restart_ecs_instance` |
| Manage | R1 — preview + confirm | `huawei_delete_ecs_instance` |

**Scope boundaries:**

- ✅ Query ECS instances, flavors, images, quotas (read-only)
- ✅ Diagnose ECS create failures (quota → flavor → image → network → keypair → disk) and
  analyze instance health (status / disk / network)
- ✅ Create (post-paid), start, stop, restart, delete ECS instances (R2/R1: always preview + confirm)
- ❌ NEVER change VPC/subnet/security group/disk resources themselves — diagnosis and create
  parameters only read them (use dedicated VPC / EVS skills for mutation)
- ❌ NEVER execute start/stop/restart/delete/create without explicit user confirmation
- ❌ NEVER echo credentials (AK/SK, passwords, tokens) in any output or report

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
     `vpc:subnets:list`, `vpc:securityGroups:list`, `vpc:publicIps:list`, `evs:volumes:list`
   - Manage: `ecs:cloudServers:create`, `ecs:cloudServers:action` (start/stop/restart),
     `ecs:cloudServers:delete`
4. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify target → region, instance_id / flavor_id / image_id / vpc_id / subnet_id / key_name, intent keywords
2. Classify intent →
     - Query/Diagnose (R3): list / show / analyze / diagnose — auto execute
     - Manage (R2): create / start / stop / restart — ALWAYS show preview and ask for explicit confirmation
     - Manage (R1): delete — ALWAYS show the instance details, irreversible warning, explicit confirmation
3. Execute → build the hcloud command from the verified templates below
4. Output → structured JSON summary + readable diagnosis report
5. Report quality → automatic via skill-quality-cli run wrapping (see Step 0 / Prerequisites #4)
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_ecs_instance`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`,
  `huawei_restart_ecs_instance`): show the full command, the target instance(s), and ask "confirm?"
  before running.
- **R1 action** (`huawei_delete_ecs_instance`): first run the read-only check
  (`ShowServer` to confirm the instance exists and record its status/flavor/volumes). Show the full
  command with the irreversible deletion warning, and require explicit confirmation before running.
- **Create preflight**: before `huawei_create_ecs_instance`, ALWAYS run
  `huawei_diagnose_ecs_create_failure` (or at least the quota + flavor + image checks) so the user
  sees the environment is ready, then confirm.

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

`ShowServerLimits` returns absolute limits and usage (e.g. `maxTotalInstances`/`totalInstancesUsed`,
`maxTotalCores`, `maxTotalRAMSize`, `maxTotalVolumes`, `maxTotalKeypairs`). For disk volume quotas,
additionally use:

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
| 1 | Quota | `hcloud ECS ShowServerLimits --cli-region={region}` | usage < limit for instances/cores/RAM/volumes | `Insufficient quota` → raise quota in console |
| 2 | Flavor | `hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}` | flavor returned; if an AZ was requested, re-check with `--availability_zone={az}` | `FlavorNotFound`/sold out → pick another flavor/AZ |
| 3 | Image | `hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active` | image exists and `active`; check `__os_type`/`architecture` matches flavor | image deleted/private mismatch → pick another image |
| 4 | Network | `hcloud VPC ListSubnets --cli-region={region}`; `hcloud VPC ListSecurityGroups/v2 --cli-region={region}`; if EIP requested `hcloud EIP ListPublicips/v2 --cli-region={region}` | subnet exists with free IPs; security group exists; EIP quota available | subnet/SG missing or no free IPs → fix network params |
| 5 | Keypair | `hcloud KPS ListKeypairs --cli-region={region}` | the `key_name` used in the request exists | `KeypairNotFound` → create keypair or drop `key_name` |
| 6 | Disk | `hcloud EVS ListVolumes --cli-region={region}`; cross-check volume quota from step 1 | volume type available in the AZ, quota not exhausted | disk type unavailable → change volumetype/AZ |

Dual-form examples:

```bash
# Step 1 — quota
hcloud ECS ShowServerLimits --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServerLimits --cli-region={region}
# Step 2 — flavor
hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
# Step 3 — image
hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active
# Step 4 — network
hcloud VPC ListSubnets --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud VPC ListSubnets --cli-region={region}
hcloud VPC ListSecurityGroups/v2 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud VPC ListSecurityGroups/v2 --cli-region={region}
# Step 5 — keypair
hcloud KPS ListKeypairs --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud KPS ListKeypairs --cli-region={region}
# Step 6 — disk
hcloud EVS ListVolumes --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS ListVolumes --cli-region={region}
```

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
# Step 4 — bound security groups & EIPs
hcloud EIP ListPublicips/v2 --cli-region={region} --port_id.{n}={port_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP ListPublicips/v2 --cli-region={region} --port_id.{n}={port_id}
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

```bash
--server.availability_zone={az}            # pin an AZ when the flavor/image require it
--server.nics.1.subnet_id={subnet_id}      # NIC subnet (defaults to VPC default subnet)
--server.security_groups.1.id={sg_id}      # security group (defaults to default SG)
--server.key_name={key_name}               # login keypair (mutually exclusive with adminPass)
--server.adminPass={password}              # or a login password (never echo it back)
--server.count={n}                         # number of instances (default 1)
--server.data_volumes.1.size={size_gb}     # extra data volume size
--server.data_volumes.1.volumetype={SATA|SAS|GPSSD}
--server.publicip.eip.bandwidth.size={mbps}      # bind a new EIP with bandwidth (Mbps)
--server.publicip.eip.bandwidth.sharetype={PER|WHOLE}
--server.user_data={base64}                # cloud-init user data (base64)
--dry_run=true                             # validate the request without creating
```

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

## Security Considerations

- **Credentials**: never output AK/SK, passwords, or tokens. `adminPass` is never echoed back.
- **Confirmation**: every write operation requires explicit user confirmation; never chain writes.
- **Delete safety**: `huawei_delete_ecs_instance` warns about `--delete_volume`/`--delete_publicip`
  data loss before execution.
- **Least privilege**: use the policies in `references/iam-policies.md`; do not grant
  `ECS FullAccess` when read-only diagnosis is enough.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — CLI installation and configuration
- `references/verification-method.md` — Verification method details
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/dataflow-diagram.md` — Mermaid data flow diagram