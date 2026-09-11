---
name: huawei-cloud-dds-dcs-instance-management
description: |
  Huawei Cloud DDS (Document Database Service) and DCS (Distributed Cache Service) unified management skill. Provides 16 operations across five capability domains: (1) Query — list/get DDS/DCS instances, DCS node info, DCS custom templates; (2) Analysis — analyze DDS deployment architecture and DCS security posture; (3) DDS Management — create instance, add read-only/sharding nodes, create backup, delete instance; (4) DCS Management — create instance, create custom template, delete instance, restart instance; (5) Multi-mode execution using hcloud CLI for available operations and huaweicloudsdk Python SDK as fallback. Auth via AK/SK environment variables or hcloud profile. All mutating operations require explicit user confirmation.
  Triggers include: "DDS","DCS","文档数据库","分布式缓存","数据库实例","缓存实例","MongoDB","Redis","Memcached","DDS实例","DCS实例","数据库运维","缓存运维","文档数据库查询","分布式缓存查询","DDS管理","DCS管理","缓存节点","自定义模板","document database","distributed cache","DDS instances","DCS instances","MongoDB cluster","Redis cache","dds-dcs".
tags: [huawei-cloud, dds, dcs, database, cache]
---

# Huawei Cloud DDS & DCS Management Skill

> Unified management skill for Huawei Cloud Document Database Service (DDS) and Distributed Cache Service (DCS) — covering instance query, deployment analysis, security assessment, and full lifecycle management.

---

## Overview

This skill provides comprehensive management for two Huawei Cloud middleware services:

| Service | Engine Types | Category |
|---------|-------------|----------|
| **DDS** (Document Database Service) | DDS-Community, DDS-Enhanced | MongoDB-compatible document DB |
| **DCS** (Distributed Cache Service) | Redis, Memcached | In-memory cache |

### Capability Matrix

| # | Action | Service | Mode | Severity |
|---|--------|---------|------|----------|
| 1 | `huawei_list_dds_instances` | DDS | CLI | R3 Query |
| 2 | `huawei_get_dds_instance` | DDS | CLI | R3 Query |
| 3 | `huawei_list_dcs_instances` | DCS | CLI | R3 Query |
| 4 | `huawei_get_dcs_nodes_information` | DCS | SDK | R3 Query |
| 5 | `huawei_list_dcs_custom_templates` | DCS | SDK | R3 Query |
| 6 | `huawei_analyze_dds_deployment` | DDS | CLI | R3 Analysis |
| 7 | `huawei_analyze_dcs_security` | DCS | CLI+SDK | R3 Analysis |
| 8 | `huawei_create_dds_instance` | DDS | CLI | R2 Mgmt |
| 9 | `huawei_add_dds_readonly_node` | DDS | CLI | R2 Mgmt |
| 10 | `huawei_add_dds_sharding_node` | DDS | CLI | R2 Mgmt |
| 11 | `huawei_create_dds_backup` | DDS | CLI | R2 Mgmt |
| 12 | `huawei_create_dcs_instance` | DCS | SDK | R2 Mgmt |
| 13 | `huawei_create_dcs_custom_template` | DCS | SDK | R2 Mgmt |
| 14 | `huawei_delete_dds_instance` | DDS | CLI | R1 Mgmt |
| 15 | `huawei_delete_dcs_instance` | DCS | CLI | R1 Mgmt |
| 16 | `huawei_restart_dcs_instance` | DCS | CLI | R1 Mgmt |

### Architecture

```
User Request → Action Router
  ├── DDS Actions → hcloud DDS CLI (primary) → SDK fallback
  └── DCS Actions → hcloud DCS CLI (primary) → SDK fallback (create_instance,
       show_nodes_information, list_config_templates, create_custom_template)
       → Result Formatting → Analysis & Recommendations
```

---

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | Installed and authenticated. See `references/cli-installation-guide.md` |
| **Python 3.8+** | For SDK fallback operations (DCS) |
| **SDK packages** | `pip install huaweicloudsdkdcs huaweicloudsdkdds` |
| **AK/SK Auth** | `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY` or `HWC_AK`/`HWC_SK` env vars |
| **IAM Permissions** | DDS and DCS read/write perms. See `references/iam-policies.md` |
| **Default Region** | `cn-north-4` (override with `--cli-region`) |

### Quality Reporting Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint (default: skillsapi.developer.myhuaweicloud.com) |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set `1` to disable (local debugging) |
| `SKILL_QUALITY_TIMEOUT` | No | Timeout seconds (default 3) |

---

## Workflow

### Query (R3) — Instance Listing & Details

```bash
# List DDS instances (all, with optional filters)
hcloud DDS ListInstances --cli-region={region}
hcloud DDS ListInstances --cli-region={region} --datastore_type=DDS-Community
hcloud DDS ListInstances --cli-region={region} --id={instance_id}  # single instance
# Filter by deployment mode. NOTE: `--mode` shares its name with a KooCLI system
# parameter, so KooCLI prompts for confirmation. Interactive: type `b` (target API
# parameter) when prompted. Non-interactive/scripted: pipe the answer (verified):
echo b | hcloud DDS ListInstances --cli-region={region} --mode=ReplicaSet
# KooCLI-recommended alternative for non-interactive environments: pass the
# parameter via a JSON input file (verified; note --project_id is required
# on the cli-jsonInput path):
#   echo '{"query": {"mode": "ReplicaSet"}}' > /tmp/dds_mode.json
#   hcloud DDS ListInstances --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dds_mode.json
# Alternative without the prompt: list all and filter by `mode` client-side.

# List DCS instances
hcloud DCS ListInstances --cli-region={region}
hcloud DCS ListInstances --cli-region={region} --name={name}
hcloud DCS ListInstances --cli-region={region} --instance_id={id}
hcloud DCS ListInstances --cli-region={region} --status={status}
# Note: `capacity` is NOT a filter of DCS ListInstances — it is only a
# Create-time parameter. Filter the returned JSON by capacity client-side if needed.
```

### Query (R3) — DCS Node Information (SDK)

> Fallback path when the CLI cannot be used. Requires `pip install huaweicloudsdkdcs`.

```python
# Service: DCS (huaweicloudsdkdcs.v2)
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdcs.v2.model import ShowNodesInformationRequest
from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion

creds = BasicCredentials().with_ak('{ak}').with_sk('{sk}')
client = DcsClient.new_builder() \
    .with_credentials(creds) \
    .with_region(DcsRegion.value_of('cn-north-4')) \
    .build()

request = ShowNodesInformationRequest(instance_id='{instance_id}')
response = client.show_nodes_information(request)
print(response)
```

### Query (R3) — List Custom Templates (SDK)

```python
# Service: DCS (huaweicloudsdkdcs.v2)
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdcs.v2.model import ListConfigTemplatesRequest
from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion

creds = BasicCredentials().with_ak('{ak}').with_sk('{sk}')
client = DcsClient.new_builder() \
    .with_credentials(creds) \
    .with_region(DcsRegion.value_of('cn-north-4')) \
    .build()

# `type` is required: 'user' for custom templates, 'sys' for system templates.
# `engine_version` and `cache_mode` are also required — omitting them returns
# DCS.4063 (missing required parameters).
request = ListConfigTemplatesRequest(
    type='user', engine='Redis', engine_version='5.0', cache_mode='single')
response = client.list_config_templates(request)
print(response)
```

### Analysis (R3) — Analyze DDS Deployment

Combines multiple queries to assess deployment architecture:

```bash
# Step 1: List all instances to understand topology
hcloud DDS ListInstances --cli-region={region} --limit=100

# Step 2: Check available flavors and storage types
hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community
hcloud DDS ListStorageType --cli-region={region}

# Step 3: For each instance, check config and backup policy
# `--entity_id` is required: pass the instance ID for replica set / single-node,
# or the group ID / node ID for cluster (sharding) instances.
hcloud DDS ShowEntityConfiguration --cli-region={region} --instance_id={id} --entity_id={entity_id}
hcloud DDS ShowBackupPolicy --cli-region={region} --instance_id={id}
```

### Analysis (R3) — Analyze DCS Security

```bash
# Step 1: List instances to inventory
hcloud DCS ListInstances --cli-region={region}

# Step 2: Check IP whitelist per instance
hcloud DCS ShowIpWhitelist --cli-region={region} --instance_id={id}

# Step 3: Check instance details (security group, SSL)
hcloud DCS ShowInstance --cli-region={region} --instance_id={id}

# Step 4: Check ACL accounts
hcloud DCS ListAclAccounts --cli-region={region} --instance_id={id}

# Step 5: (SDK fallback) Inspect SSL/connection details via SDK — see the
# "DCS Node Information (SDK)" example below; replace the request with ShowInstanceRequest.
```

### Management (R2) — Create DDS Instance

> ⚠️ Creates billable resources. **Always confirm with the user first.**

```bash
# Replica set (3 nodes)
# NOTE: `--region` is a required body parameter of DDS CreateInstance — keep it.
# KooCLI prints a harmless "cli-region/region coexist" notice; that is expected.
# `--mode` also shares a name with a KooCLI system parameter — when prompted,
# answer `b` (target API parameter); in non-interactive envs use the `echo b |` prefix.
echo b | hcloud DDS CreateInstance --cli-region={region} \
  --name=my-dds --region={region} \
  --availability_zone={az} \
  --datastore.type=DDS-Community \
  --datastore.version=5.0 --datastore.storage_engine=wiredTiger \
  --mode=ReplicaSet \
  --flavor.1.type=replica --flavor.1.num=3 \
  --flavor.1.spec_code={spec_code} \
  --subnet_id={subnet} --security_group_id={sg}

# Single node
echo b | hcloud DDS CreateInstance --cli-region={region} \
  --name=my-dds-single --region={region} \
  --availability_zone={az} \
  --datastore.type=DDS-Community \
  --datastore.version=5.0 --datastore.storage_engine=wiredTiger \
  --mode=Single \
  --flavor.1.type=single --flavor.1.num=1 \
  --flavor.1.spec_code={spec_code} \
  --subnet_id={subnet} --security_group_id={sg}
```

### Management (R2) — Add DDS Read-only Node

> ⚠️ Adds billable nodes. Confirm with user.

```bash
hcloud DDS AddReadonlyNode --cli-region={region} \
  --instance_id={instance_id} --num=1
```

### Management (R2) — Add DDS Sharding Node

> ⚠️ Modifies cluster capacity. Confirm with user.

```bash
hcloud DDS AddShardingNode --cli-region={region} \
  --instance_id={instance_id} --type=shard --num=2 --spec_code={spec}

hcloud DDS AddShardingNode --cli-region={region} \
  --instance_id={instance_id} --type=mongos --num=2 --spec_code={spec}
```

### Management (R2) — Create DDS Backup

```bash
hcloud DDS CreateManualBackup --cli-region={region} \
  --backup.instance_id={instance_id} --backup.name={backup_name}
```

### Management (R2) — Create DCS Instance (SDK)

> ⚠️ Creates billable resources. Confirm with user. Requires `pip install huaweicloudsdkdcs`.

```python
# Service: DCS (huaweicloudsdkdcs.v2)
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdcs.v2.model import CreateInstanceBody, CreateInstanceRequest
from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion

creds = BasicCredentials().with_ak('{ak}').with_sk('{sk}')
client = DcsClient.new_builder() \
    .with_credentials(creds) \
    .with_region(DcsRegion.value_of('cn-north-4')) \
    .build()

body = CreateInstanceBody(
    name="my-redis-instance",
    engine="Redis",
    engine_version="5.0",
    capacity=1,
    vpc_id="{vpc_id}",
    subnet_id="{subnet_id}",
    security_group_id="{sg_id}",
    az_codes=["{az_code}"],
)
request = CreateInstanceRequest(body=body)
response = client.create_instance(request)
print(response)
```

### Management (R2) — Create DCS Custom Template (SDK)

> ⚠️ Confirm with user. Requires `pip install huaweicloudsdkdcs`.

```python
# Service: DCS (huaweicloudsdkdcs.v2)
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdcs.v2.model import CreateCustomTemplateBody, CreateCustomTemplateRequest
from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion

creds = BasicCredentials().with_ak('{ak}').with_sk('{sk}')
client = DcsClient.new_builder() \
    .with_credentials(creds) \
    .with_region(DcsRegion.value_of('cn-north-4')) \
    .build()

# Required body fields: name, engine, cache_mode; engine_version and template_id
# (source template) are strongly recommended. `type` = 'user' for custom templates.
body = CreateCustomTemplateBody(
    name="my-template",
    type="user",
    engine="Redis",
    engine_version="5.0",
    cache_mode="single",
    description="my custom template",
    params={"timeout": "300"},
    template_id="{source_template_id}",
)
request = CreateCustomTemplateRequest(body=body)
response = client.create_custom_template(request)
print(response)
```

### Management (R1) — Delete DDS Instance

> ⚠️ **Permanently deletes instance and ALL data. Double-confirm with user.**

```bash
hcloud DDS DeleteInstance --cli-region={region} --instance_id={instance_id}
```

### Management (R1) — Delete DCS Instance

> ⚠️ **Permanently deletes cache and ALL data. Double-confirm with user.**

```bash
hcloud DCS DeleteSingleInstance --cli-region={region} --instance_id={id}
```

### Management (R1) — Restart DCS Instance

> ⚠️ Causes service interruption. `action=flush` deletes cached data.

```bash
# Force restart
hcloud DCS RestartOrFlushInstances --cli-region={region} \
  --instances.1={instance_id} --action=restart

# Soft restart (process only)
hcloud DCS RestartOrFlushInstances --cli-region={region} \
  --instances.1={instance_id} --action=soft_restart

# Restart multiple instances
hcloud DCS RestartOrFlushInstances --cli-region={region} \
  --instances.1={id1} --instances.2={id2} --action=restart
```

---

## KooCLI Command Format Standard

> **格式模板（占位示例，不可直接执行）**：`hcloud DDS|DCS <Operation> --cli-region=<region> [--key=value ...]`

| Feature | Description | Example |
|---------|-------------|---------|
| Service | Service name (uppercase) | `DDS`, `DCS` |
| Operation | PascalCase | `ListInstances`, `CreateInstance` |
| Region | `--cli-region=value` | `cn-north-4` |
| Simple param | `--key=value` | `--instance_id=xxx` |
| Indexed param | `--key.N=value` | `--flavor.1.num=3` |
| Nested param | `--parent.child=value` | `--datastore.type=DDS-Community` |

All mutating operations must include `--project_id` (auto-resolved from hcloud profile).

---

## Parameter Confirmation

See `references/related-commands.md` for detailed parameter tables per action.

| Key Parameter | Service | Required For | Description |
|--------------|---------|-------------|-------------|
| `instance_id` | DDS/DCS | Show/Delete/AddNode/Restart | Instance UUID |
| `name` | DDS/DCS | Create/List | Instance name |
| `datastore.*` | DDS | Create | Database type, version, engine |
| `flavor.[N].*` | DDS | Create/AddNode | Node type, count, spec |
| `capacity` | DCS | Create | Cache capacity (GB) |
| `engine` | DCS | Create/Templates | `Redis` or `Memcached` |
| `type` (template) | DCS | List/Create | Template scope: `sys` or `user` |
| `action` | DCS | Restart | `restart`, `soft_restart`, or `flush` |

---

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution quality reporting. Every run reports trace_id, status (success/biz_fail/sys_fail/cancel), error code, cost, and masked input/output.

### Integration
- **Python entry point:** wrap with `quality_context`:
  ```python
  from skill_quality_sdk import quality_context
  with quality_context(skill_name="huawei-cloud-dds-dcs-instance-management") as q:
      q.input = {...}
      result = do_something()
      q.output = result
  ```
- **CLI-only:** SDK vendored in `scripts/` for future wrapper use.

### Error Code Convention
| Prefix | Category | Examples |
|--------|----------|----------|
| U | User input | U01 missing param, U03 no data |
| C | Config | C01 missing AK/SK |
| N | Network | N01 timeout |
| B | Code bug | B01 null pointer |
| P | Platform | P01 scheduler error |

Non-blocking, fail-silent. Disable via `SKILL_QUALITY_DISABLE=1`.

---

## Critical Warnings

| Action | Warning |
|--------|---------|
| `create_dds_instance` / `create_dcs_instance` | Creates billable resources. Always confirm with user. |
| `add_dds_readonly_node` / `add_dds_sharding_node` | Adds billable nodes. Confirm count/spec with user. |
| `delete_dds_instance` / `delete_dcs_instance` | **Permanently deletes ALL data.** Double-confirm; recommend backup. |
| `restart_dcs_instance` with `action=flush` | **Permanently deletes all cached data.** Confirm action type. |

---

## Authentication

### Mode 1: AK/SK Environment Variables

```bash
export HUAWEI_ACCESS_KEY=your-access-key
export HUAWEI_SECRET_KEY=your-secret-key
# Or legacy:
export HWC_AK=your-access-key; export HWC_SK=your-secret-key
```

### Mode 2: hcloud CLI Profile

```bash
hcloud configure set --cli-profile=default \
  --access-key=your-access-key --secret-key=your-secret-key
hcloud configure set --cli-profile=default --cli-region=cn-north-4
```

---

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — CLI install & config
- `references/verification-method.md` — Verification details
- `references/dataflow-diagram.md` — Data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/related-commands.md` — Full command reference