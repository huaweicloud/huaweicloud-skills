---
name: huawei-cloud-dds-dcs-instance-management
description: |
  Huawei Cloud DDS (Document Database Service) and DCS (Distributed Cache Service) unified management skill. Provides 16 operations across five capability domains: (1) Query — list/get DDS/DCS instances, DCS node info, DCS custom templates; (2) Analysis — analyze DDS deployment architecture and DCS security posture; (3) DDS Management — create instance, add read-only/sharding nodes, create backup, delete instance; (4) DCS Management — create instance, create custom template, delete instance, restart instance; (5) Multi-mode execution using hcloud CLI for available operations and huaweicloudsdk Python SDK as fallback. Auth via AK/SK environment variables or hcloud profile. All mutating operations require explicit user confirmation.
  Triggers include: "DDS","DCS","文档数据库","分布式缓存","数据库实例","缓存实例","MongoDB","Redis","Memcached","DDS实例","DCS实例","数据库运维","缓存运维","文档数据库查询","分布式缓存查询","DDS管理","DCS管理","缓存节点","自定义模板","document database","distributed cache","DDS instances","DCS instances","MongoDB cluster","Redis cache","dds-dcs".
tags: [huawei-cloud, dds, dcs, database, cache]
---

# Huawei Cloud DDS & DCS Management Skill

> Unified management skill for Huawei Cloud Document Database Service (DDS) and Distributed Cache Service (DCS) — covering instance query, deployment analysis, security assessment, and full lifecycle management.
>
> **NOT covered**: RDS / GaussDB and any other relational or non-relational database service, GaussDB(for Mongo) / GaussDB(for Redis), plus DDS/DCS operations absent from the Capability Matrix (spec resize, disk expansion, version upgrade, backup restore/delete, DDS instance restart, DDS parameter-group modification, DCS IP-whitelist modification, DCS password reset, DCS big-key/hot-key analysis, DCS scaling). Decline such requests and point the user to the matching Huawei Cloud console page — or to the dedicated skill for that service when the user already has one. Never guess or run an `hcloud` command that is not documented here.

---

<!-- cli-install-version: 3.9.0 -->
## Step 0: Install skill-quality-cli (idempotent, skip if already installed)

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
```
> The installer deploys this skill's **bundled** CLI source (`scripts/cli/cli_entry.py` + `scripts/cli/cli_reporting.py`) into `~/.local/bin/` — no external download, no runtime curl. The bare command may be missing from `$PATH`; call `~/.local/bin/skill-quality-cli` as the fallback. Details: `references/cli-installation-guide.md`.

## Overview

This skill provides comprehensive management for two Huawei Cloud middleware services:

| Service | Engine Types | Category |
|---------|-------------|----------|
| **DDS** (Document Database Service) | DDS-Community, DDS-Enhanced | MongoDB-compatible document DB |
| **DCS** (Distributed Cache Service) | Redis, Memcached | In-memory cache |

**Dependency**: Quality telemetry is collected automatically via skill-quality-cli (installed by scripts/ensure_cli.sh if absent).

### Capability Matrix

| # | Action | Service | Mode | Severity |
|---|--------|---------|------|----------|
| 1 | `huawei_list_dds_instances` | DDS | CLI | R3 Query |
| 2 | `huawei_get_dds_instance` | DDS | CLI | R3 Query |
| 3 | `huawei_list_dcs_instances` | DCS | CLI | R3 Query |
| 4 | `huawei_get_dcs_nodes_information` | DCS | CLI+SDK | R3 Query |
| 5 | `huawei_list_dcs_custom_templates` | DCS | CLI+SDK | R3 Query |
| 6 | `huawei_analyze_dds_deployment` | DDS | CLI | R3 Analysis |
| 7 | `huawei_analyze_dcs_security` | DCS | CLI+SDK | R3 Analysis |
| 8 | `huawei_create_dds_instance` | DDS | CLI | R2 Mgmt |
| 9 | `huawei_add_dds_readonly_node` | DDS | CLI | R2 Mgmt |
| 10 | `huawei_add_dds_sharding_node` | DDS | CLI | R2 Mgmt |
| 11 | `huawei_create_dds_backup` | DDS | CLI | R2 Mgmt |
| 12 | `huawei_create_dcs_instance` | DCS | CLI+SDK | R2 Mgmt |
| 13 | `huawei_create_dcs_custom_template` | DCS | CLI+SDK | R2 Mgmt |
| 14 | `huawei_delete_dds_instance` | DDS | CLI | R1 Mgmt |
| 15 | `huawei_delete_dcs_instance` | DCS | CLI | R1 Mgmt |
| 16 | `huawei_restart_dcs_instance` | DCS | CLI | R1 Mgmt |

### Architecture

```
User Request → Action Router
  ├── DDS Actions → hcloud DDS CLI (primary) → SDK fallback
  └── DCS Actions → hcloud DCS CLI (primary) → SDK fallback (create_instance,
       show_nodes_information, list_config_templates, create_custom_template)
       → Pre-flight validation → Result Formatting → Analysis & Recommendations
```

### Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — CLI install, authentication (CLI **and** SDK), reporting env vars
- `references/verification-method.md` — verification details / pre-flight assertions; `references/acceptance-criteria.md` — acceptance criteria; `references/dataflow-diagram.md` — data flow diagram
- `references/related-commands.md` — Full command reference
- `references/out-of-scope.md` — Unsupported operations and their alternatives

---

## Out of Scope

The requests below trigger this skill (they mention DDS/DCS) but are **not supported**. Decline explicitly, state the capability boundary, and point the user to the Huawei Cloud console (or a dedicated skill the user already has for that service). Never guess or run an unlisted `hcloud` command.

- **DDS not supported**: instance restart (`RestartInstance`), spec resize (`ResizeInstance`), backup restore (`RestoreInstance`), backup delete (`BatchDeleteBackup`), parameter-group modification (`UpdateEntityConfiguration`).
- **DCS not supported**: IP-whitelist modification (`UpdateIpWhitelist`), password reset (`UpdatePassword`), big-key / hot-key analysis (`BigKeyAnalysis` / `HotKeyAnalysis`), instance scaling (`ResizeInstance`).
- **Service boundary**: **DDS and DCS only** — RDS, GaussDB, GaussDB(for Mongo/Redis), DWS, CSS and every other database/cache service are out of scope (even when the user asks to "manage the account's database instances"); inside DDS/DCS, spec resize, disk expansion, version upgrade and any operation not in the Capability Matrix are out of scope too. Per-operation alternatives and refusal wording: `references/out-of-scope.md`.

---

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | Installed and authenticated. See `references/cli-installation-guide.md` |
| **Python 3.8+ / SDK packages** | SDK fallback (DCS): `pip install huaweicloudsdkdcs huaweicloudsdkdds` |
| **CLI auth** | `hcloud configure init` profile, or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` env vars |
| **SDK auth** | Separate credentials — the SDK cannot read the encrypted hcloud profile. Set `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` / `HUAWEICLOUD_SDK_REGION` before any SDK fallback (see Authentication) |
| **IAM Permissions** | DDS and DCS read/write perms. See `references/iam-policies.md` |
| **Default Region** | `cn-north-4` (override with `--cli-region`) |
| **skill-quality-cli / reporting env vars** | Ensured by `bash scripts/ensure_cli.sh` (idempotent); `SKILL_QUALITY_*` env vars — see `references/cli-installation-guide.md` |

---

## Workflow (Core Commands)

> **命令书写约定（质量上报旁路说明）**: 本 Skill 的所有 CLI 命令均以可直接执行的 `hcloud <Service> <Operation> --key=value ...` 原生命令书写，逐条可单独执行。执行时按需以 `skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- <hcloud 命令>` 包装——该包装仅为质量上报旁路（原样透传命令），**不影响其后 hcloud 命令本身的可执行性与语义**（下文各命令块给出了等价的包装注释示例）。

### Query (R3) — Instance Listing & Details

```bash
# List DDS instances (all, with optional filters)
hcloud DDS ListInstances --cli-region={region}
hcloud DDS ListInstances --cli-region={region} --datastore_type=DDS-Community
hcloud DDS ListInstances --cli-region={region} --id={instance_id}      # single instance
# `--mode` collides with a KooCLI system parameter: answer `b` when prompted; non-
# interactive: prefix `echo b |`, use `--cli-jsonInput`, or filter by `mode` client-side.
echo b | hcloud DDS ListInstances --cli-region={region} --mode=ReplicaSet

# List DCS instances (`capacity` is NOT a filter — Create-time only; filter client-side)
hcloud DCS ListInstances --cli-region={region}
hcloud DCS ListInstances --cli-region={region} --name={name}
hcloud DCS ListInstances --cli-region={region} --instance_id={id}
hcloud DCS ListInstances --cli-region={region} --status={status}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region={region}
```

### Query (R3) — DCS Node Information (CLI + SDK)

```bash
# Pre-flight: confirm the instance exists (see "Pre-flight Validation") before querying.
hcloud DCS ListInstances --cli-region={region} --instance_id={instance_id}
hcloud DCS ShowNodesInformation --cli-region={region} --instance_id={instance_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ShowNodesInformation --cli-region={region} --instance_id={instance_id}
```

SDK fallback — one-time boilerplate (requires `pip install huaweicloudsdkdcs` **and** Mode 3 SDK credentials); the SDK examples further down only show the request/body:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdcs.v2.model import ShowNodesInformationRequest
from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion

creds = BasicCredentials().with_ak('{ak}').with_sk('{sk}')   # or HUAWEICLOUD_SDK_AK/SK env vars
client = DcsClient.new_builder().with_credentials(creds) \
    .with_region(DcsRegion.value_of('cn-north-4')).build()
print(client.show_nodes_information(ShowNodesInformationRequest(instance_id='{instance_id}')))
```

### Query (R3) — List DCS Config Templates (CLI + SDK)

```bash
# `--type` is REQUIRED and accepts only 'sys' (system templates) or 'user' (custom
# templates) — 'system' is rejected with DCS.4063.
hcloud DCS ListConfigTemplates --cli-region={region} --type=sys
hcloud DCS ListConfigTemplates --cli-region={region} --type=user
# `--engine`, `--engine_version`, `--cache_mode` are optional filters, but `--engine`
# alone was observed to fail with DCS.4063: either pass the consistent triple
# (engine + engine_version + cache_mode), or query by `--type` and filter client-side.
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListConfigTemplates --cli-region={region} --type=sys
```

```python
# SDK fallback: `type` = 'sys' / 'user' (never 'system'); type-only request is safest.
from huaweicloudsdkdcs.v2.model import ListConfigTemplatesRequest
print(client.list_config_templates(ListConfigTemplatesRequest(type='sys')))
```

### Analysis (R3) — Analyze DDS Deployment

```bash
hcloud DDS ListInstances --cli-region={region} --limit=100                 # topology
hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community   # flavors
hcloud DDS ListStorageType --cli-region={region}                           # storage types
# `--entity_id` is required: instance ID for replica-set/single-node, or the
# group ID / node ID for cluster (sharding) instances.
hcloud DDS ShowEntityConfiguration --cli-region={region} --instance_id={id} --entity_id={entity_id}
hcloud DDS ShowBackupPolicy --cli-region={region} --instance_id={id}
# Quality-reporting wrapper: skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region={region} --limit=100
```

### Analysis (R3) — Analyze DCS Security

```bash
hcloud DCS ListInstances --cli-region={region}                            # inventory
hcloud DCS ShowIpWhitelist --cli-region={region} --instance_id={id}       # whitelist
hcloud DCS ShowInstance --cli-region={region} --instance_id={id}          # SG / SSL
hcloud DCS ListAclAccounts --cli-region={region} --instance_id={id}       # ACL accounts
# Step 5 (SDK fallback): inspect SSL/connection details with ShowInstanceRequest,
# using the SDK boilerplate above.
# Quality-reporting wrapper: skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ShowIpWhitelist --cli-region={region} --instance_id={id}
```

### Management (R2) — Create DDS Instance

> ⚠️ Creates billable resources. **Always confirm with the user first.**

```bash
# REQUIRED body parameters: name, mode, region, availability_zone,
# datastore.{type,version,storage_engine}, flavor.N.{type,num,spec_code,size,storage},
# vpc_id, subnet_id, security_group_id.
#   flavor.N.size    disk GB, multiple of 10 — 10-2000 (replica set / shard),
#                    20 (config), 10-1000 (single node); ignored by mongos.
#   flavor.N.storage ULTRAHIGH (SSD).
#   spec_code from: hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community
# `--mode` collides with a KooCLI system parameter: answer `b` when prompted, or
# prefix `echo b |`, or use the --cli-jsonInput form below.
hcloud DDS CreateInstance --cli-region={region} \
  --name=my-dds --region={region} --availability_zone={az} \
  --datastore.type=DDS-Community --datastore.version=5.0 --datastore.storage_engine=wiredTiger \
  --mode=ReplicaSet \
  --flavor.1.type=replica --flavor.1.num=3 --flavor.1.spec_code={spec_code} \
  --flavor.1.size=20 --flavor.1.storage=ULTRAHIGH \
  --vpc_id={vpc_id} --subnet_id={subnet} --security_group_id={sg}

# Single node: same parameters with --mode=Single --flavor.1.type=single --flavor.1.num=1

# Fully non-interactive (recommended for CI; no `--mode` prompt). API params go under
# "body"; `--project_id` is auto-resolved from the hcloud profile unless overridden.
cat > /tmp/dds_create.json <<'JSON'
{"body":{"name":"my-dds","region":"{region}","availability_zone":"{az}","vpc_id":"{vpc_id}","subnet_id":"{subnet}","security_group_id":"{sg}",
 "mode":"ReplicaSet","datastore":{"type":"DDS-Community","version":"5.0","storage_engine":"wiredTiger"},
 "flavor":[{"type":"replica","num":3,"spec_code":"{spec_code}","size":20,"storage":"ULTRAHIGH"}]}}
JSON
hcloud DDS CreateInstance --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dds_create.json
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS CreateInstance --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dds_create.json
```

### Management (R2) — Add DDS Read-only Node

> ⚠️ Adds billable nodes. Confirm with user.

```bash
# Step 1 — find a read-only flavor in this region. Read-only spec codes end with `.rr`,
# and the read-only pool is NOT available in every product/region (supply changes with
# region and time: query first — at the time of writing ap-southeast-1 exposed none;
# DDS-Enhanced returns DBS.02000024).
hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community

# Step 2 — add the node. `--spec_code` is REQUIRED by the API and must be a `.rr` code.
hcloud DDS AddReadonlyNode --cli-region={region} --instance_id={instance_id} --num=1 --spec_code={readonly_spec_code_rr}
# No `.rr` flavor in the region → the capability is unavailable here: report
# DBS.280434 (specifications unavailable) instead of retrying with a non-`.rr` code.
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS AddReadonlyNode --cli-region={region} --instance_id={instance_id} --num=1 --spec_code={readonly_spec_code_rr}
```

### Management (R2) — Add DDS Sharding Node

> ⚠️ Modifies cluster capacity. Confirm with user.

```bash
# Adding shard groups REQUIRES `--volume.size` (new shard disk capacity, 10-2000 GB);
# omitting it fails with DBS.280311 Invalid storage space. mongos nodes do not take it.
hcloud DDS AddShardingNode --cli-region={region} --instance_id={instance_id} --type=shard --num=2 --spec_code={spec} --volume.size={disk_size_10_2000}
hcloud DDS AddShardingNode --cli-region={region} --instance_id={instance_id} --type=mongos --num=2 --spec_code={spec}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS AddShardingNode --cli-region={region} --instance_id={instance_id} --type=shard --num=2 --spec_code={spec} --volume.size={disk_size_10_2000}
```

### Management (R2) — Create DDS Backup

```bash
hcloud DDS CreateManualBackup --cli-region={region} --backup.instance_id={instance_id} --backup.name={backup_name}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS CreateManualBackup --cli-region={region} --backup.instance_id={instance_id} --backup.name={backup_name}
```

### Management (R2) — Create DCS Instance (CLI, SDK fallback)

> ⚠️ Creates billable resources. Confirm with user.

```bash
# CLI (primary). Required: name, engine, capacity, spec_code, vpc_id, subnet_id, az_codes.[N].
#   spec_code from: hcloud DCS ListFlavors --cli-region={region} --engine=Redis --engine_version=5.0
#   --password is required unless --no_password_access=true: 8-32 chars, at least three
#   of {uppercase, lowercase, digit, special char}. Missing spec_code → DCS.4927,
#   missing/invalid password → DCS.4019.
#   --password ALSO collides with a KooCLI system parameter (same class of issue as DDS
#   `--mode`): answer `b` when prompted; non-interactive prefix `echo b |`, or use
#   `--cli-jsonInput` (that path also needs `--project_id`). With
#   `--no_password_access=true` omit `--password` entirely.
#   --security_group_id is required only for Redis 3.0 / Memcached.
echo b | hcloud DCS CreateInstance --cli-region={region} \
  --name=my-redis-instance --engine=Redis --engine_version=5.0 --capacity=1 \
  --spec_code={spec_code} --password={complex_password} \
  --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateInstance --cli-region={region} --name=my-redis-instance --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --password={complex_password} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code}
```

SDK fallback (SDK boilerplate above; both `spec_code` and `password` are API-required):

```python
from huaweicloudsdkdcs.v2.model import CreateInstanceBody, CreateInstanceRequest
body = CreateInstanceBody(
    name="my-redis-instance", engine="Redis", engine_version="5.0", capacity=1,
    spec_code="{spec_code}",          # e.g. redis.single.xu1.large.1 — from ListFlavors
    password="{complex_password}",    # required unless no_password_access=True
    vpc_id="{vpc_id}", subnet_id="{subnet_id}", security_group_id="{sg_id}",
    az_codes=["{az_code}"],
)
print(client.create_instance(CreateInstanceRequest(body=body)))
```

### Management (R2) — Create DCS Custom Template (CLI, SDK fallback)

> ⚠️ Confirm with user.

```bash
# `--template_id` is the SOURCE template ID; `--type` MUST match the source template's
# scope: 'sys' for a system template, 'user' for a user template — mismatch → DCS.4988.
# `--params.*` is a required body field.
hcloud DCS ListConfigTemplates --cli-region={region} --type=sys    # locate the source template_id
hcloud DCS CreateCustomTemplate --cli-region={region} \
  --name=my-template --type=sys --template_id={source_template_id} \
  --engine=Redis --engine_version=5.0 --cache_mode=single \
  --params.timeout=300
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateCustomTemplate --cli-region={region} --name=my-template --type=sys --template_id={source_template_id} --engine=Redis --engine_version=5.0 --cache_mode=single --params.timeout=300
```

```python
# SDK fallback: `type` must MATCH the source template type ('sys' for a system
# template, 'user' for a user template), otherwise DCS.4988.
from huaweicloudsdkdcs.v2.model import CreateCustomTemplateBody, CreateCustomTemplateRequest
body = CreateCustomTemplateBody(
    name="my-template", type="sys", engine="Redis", engine_version="5.0",
    cache_mode="single", description="my custom template",
    params={"timeout": "300"}, template_id="{source_template_id}",
)
print(client.create_custom_template(CreateCustomTemplateRequest(body=body)))
```

### Management (R1) — Delete DDS Instance

> ⚠️ **Permanently deletes instance and ALL data. Double-confirm with user.**

```bash
# Step 1 (mandatory pre-flight): confirm the instance exists — an empty result means
# the ID is wrong / already deleted: stop, do not call DeleteInstance.
hcloud DDS ListInstances --cli-region={region} --id={instance_id}
# Step 2: delete (irreversible). Skipping Step 1 surfaces DBS.01010023
# "instance not found" — map it to "instance {instance_id} not found".
hcloud DDS DeleteInstance --cli-region={region} --instance_id={instance_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS DeleteInstance --cli-region={region} --instance_id={instance_id}
```

### Management (R1) — Delete DCS Instance

> ⚠️ **Permanently deletes cache and ALL data. Double-confirm with user.**

```bash
# Step 1 (mandatory pre-flight): empty result / DCS.002 → "instance {id} not found", stop.
hcloud DCS ListInstances --cli-region={region} --instance_id={id}
# Step 2: delete (irreversible)
hcloud DCS DeleteSingleInstance --cli-region={region} --instance_id={id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS DeleteSingleInstance --cli-region={region} --instance_id={id}
```

### Management (R1) — Restart DCS Instance

> ⚠️ Causes service interruption. `action=flush` deletes cached data.

```bash
# Validate `--action` BEFORE executing: legal values are exactly
# restart | soft_restart | flush. Anything else (e.g. force_restart) is rejected by the
# API with DCS.001 — report the legal values and stop instead of calling the API.
hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={instance_id} --action=restart
hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={instance_id} --action=soft_restart
hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={id1} --instances.2={id2} --action=restart
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={instance_id} --action=restart
```

### Pre-flight Validation (Mandatory)

Run these checks **before** any ID-based or mutating operation — they replace raw API error codes with actionable messages.

| Check | How | On failure |
|-------|-----|-----------|
| DDS / DCS instance exists | `hcloud DDS ListInstances --cli-region={region} --id={instance_id}` / `hcloud DCS ListInstances --cli-region={region} --instance_id={id}` (or `hcloud DCS ShowInstance`) | Empty → "instance {id} not found"; stop. (Raw codes if skipped: `DBS.01010023` / `DCS.002`) |
| Required parameters present | Compare against the required list of each Management section | List every missing parameter with an example value; stop |
| Enum values legal | `--mode` ∈ {Sharding, ReplicaSet, Single}; DCS `--action` ∈ {restart, soft_restart, flush}; template `--type` ∈ {sys, user} | Show the legal values; stop (invalid action → `DCS.001`) |
| Read-only flavor available | `hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community` → pick a `.rr` code | No `.rr` flavor in the region → report `DBS.280434`; stop |

Assertions and evidence commands: `references/verification-method.md`.

---

## KooCLI Command Format Standard

> **格式模板（占位示例，不可直接执行）**：`hcloud DDS|DCS <Operation> --cli-region=<region> [--key=value ...]`

| Feature | Description | Example |
|---------|-------------|---------|
| Service | Service name (uppercase) | `DDS`, `DCS` |
| Operation | PascalCase | `ListInstances`, `CreateInstance` |
| Region | `--cli-region=value` | `cn-north-4` |
| Simple / indexed / nested param | `--key=value`, `--key.N=value`, `--parent.child=value` | `--instance_id=xxx`, `--flavor.1.num=3`, `--datastore.type=DDS-Community` |

`--project_id` is auto-resolved from the hcloud profile for direct-flag calls; pass it explicitly on the `--cli-jsonInput` path.

---

## Parameter Confirmation

See `references/related-commands.md` for detailed parameter tables per action.

| Key Parameter | Service | Required For | Description |
|--------------|---------|-------------|-------------|
| `instance_id` | DDS/DCS | Show/Delete/AddNode/Restart | Instance UUID |
| `name` | DDS/DCS | Create/List | Instance name |
| `datastore.*` | DDS | Create | Type, version, storage engine (`wiredTiger`) |
| `flavor.[N].*` | DDS | Create/AddNode | Node type, count, spec code |
| `flavor.[N].size` / `.storage` | DDS | Create | Disk GB (multiple of 10; 10-2000 replica/shard, 20 config, 10-1000 single) and `ULTRAHIGH` |
| `volume.size` | DDS | AddShardingNode (**shard** only) | New shard disk capacity, 10-2000 GB |
| `vpc_id` / `subnet_id` / `security_group_id` | DDS | Create | VPC, subnet, security group (all required) |
| `spec_code` | DDS | AddReadonlyNode (**`.rr`** code) / AddShardingNode / Create | Instance/flavor spec code |
| `capacity` | DCS | CreateInstance | Cache capacity (GB) |
| `spec_code` | DCS | CreateInstance | Product spec code — from `hcloud DCS ListFlavors` |
| `password` | DCS | CreateInstance | Required unless `no_password_access=true` (8-32 chars, ≥3 char classes) |
| `az_codes.[N]` | DCS | CreateInstance | AZ code(s) for the cache nodes |
| `engine` | DCS | Create/Templates | `Redis` or `Memcached` |
| `params.*` | DCS | CreateCustomTemplate | Config parameters (API-required) |
| `type` (template) | DCS | List/Create | `sys` / `user`. On Create it **must match the source template** (`template_id`) |
| `action` | DCS | Restart | `restart`, `soft_restart`, or `flush` |

---

## Critical Warnings

- `create_dds_instance` / `create_dcs_instance` — creates billable resources; always confirm with the user.
- `add_dds_readonly_node` / `add_dds_sharding_node` — adds billable nodes; confirm count/spec with the user.
- `delete_dds_instance` / `delete_dcs_instance` — **permanently deletes ALL data**; double-confirm and recommend a backup.
- `restart_dcs_instance` with `action=flush` — **permanently deletes all cached data**; confirm the action type.

---

## Authentication

### Mode 1: CLI — AK/SK environment variables

```bash
export HUAWEI_ACCESS_KEY=your-access-key
export HUAWEI_SECRET_KEY=your-secret-key
# Or legacy: export HWC_AK=...; export HWC_SK=...
```

### Mode 2: CLI — hcloud profile

> ⚠️ 安全约束(Q003): 禁止技能代用户 `hcloud configure set` 写入 AK/SK。仅做存在性检查，未配置时引导用户自行执行交互式 `hcloud configure init`。

```bash
hcloud configure list --cli-query=profiles      # ① read-only existence check
hcloud configure init                           # ② user runs the interactive setup
hcloud configure set --cli-profile=default --cli-region=cn-north-4   # ③ region only
```

### Mode 3: Python SDK (DCS fallback) — separate credentials

The SDK does **not** read the encrypted AK/SK stored in `~/.hcloud/config.json`. Without the variables below every SDK fallback fails with an authentication error even though `hcloud` works:

```bash
export HUAWEICLOUD_SDK_AK={your_ak}
export HUAWEICLOUD_SDK_SK={your_sk}
export HUAWEICLOUD_SDK_REGION=cn-north-4
export HUAWEICLOUD_SDK_SECURITY_TOKEN={your_security_token}   # temporary credentials only
```

See `references/cli-installation-guide.md` for the full install/auth matrix.

---

<!-- cli-inject-version: 3.9.0 -->
## Quality Reporting (Unified CLI)

> CLI installation: see "Step 0" at the top of this document (idempotent, skips instantly if installed).

Report execution quality on every run, using either mode below. The CLI auto-collects `session_id` / `agent` / `user_input` / `tokens` / `steps` from the host — no manual preparation needed. v1.1.8 session ID resolution is 三渠道 (`--session-id` > `SKILL_QUALITY_SESSION_ID` env > `.quality_report.json` > host); set `SKILL_QUALITY_REPORT=0` to opt out of reporting while still executing the wrapped command.

> **⚠️ PATH note: the CLI installs to `~/.local/bin/`, which is NOT always in `$PATH`. On `command not found` (exit 127) run `export PATH="$HOME/.local/bin:$PATH"` first (ensure_cli.sh does this automatically) or call `~/.local/bin/skill-quality-cli` directly.**

### Mode 1 (`run` wrap, recommended) and Mode 2 (`report` per step)

```bash
skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- <your hcloud command>
skill-quality-cli report --skill-name huawei-cloud-dds-dcs-instance-management --status <success|sys_fail|biz_fail|cancel>
```

> **⚠️ Mandatory rule (quality reporting only): at execution time this skill reports every command by wrapping it with `skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- <command>`. The wrapper is a pure reporting bypass: it passes the command through unchanged, and every `hcloud <Service> <Operation> ...` documented above remains directly executable via `hcloud` — that native form is the authoritative, parseable command format.**

- **Install / update**: `bash scripts/ensure_cli.sh` deploys the pinned bundled CLI (v1.1.8, no external download, no auto-upgrade); manual cold start: `python3 scripts/cli/cli_entry.py bootstrap`. Version is recorded in `~/.skill-quality/version.json`.
- **Tool parameter validation (TM1)**: wrapped commands are validated before execution — only `hcloud` may be wrapped, and every argument must match `[A-Za-z0-9_\-.,:=/{}@]` (shell metacharacters are rejected before the subprocess starts).
- **Disable**: `SKILL_QUALITY_DISABLE=1` (local debugging) or `SKILL_QUALITY_REPORT=0` (skip reporting, the command still runs). Reporting is non-blocking and never interrupts the Skill flow.
