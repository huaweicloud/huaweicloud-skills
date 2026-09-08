---
name: huawei-cloud-cloudrobo-resource
description: >
  Query CloudRobo resource quotas and resource pools — list workspace-level and Domain-level
  quotas with CCE/ModelArts isolation (CCE: cpu/memory/gpu, ModelArts: npu), list resource
  pools with multi-condition filtering (type/sub-type/pool-type/usages), and show resource
  pool details with node-level information (name, status, resources, labels). Provides
  compute capacity visibility for training, evaluation, and inference workloads.
  Triggers include: resource quota query, resource pool query, resource pool list,
  resource pool detail, quota list, Domain quota aggregation, CCE quota, ModelArts quota,
  资源配额查询, 资源池查询, 资源池列表, 资源池详情, 配额查询.
tags:
  - huawei-cloud-cloudrobo
  - resource
  - quota
  - resource-pool
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview 概述

The `cloudrobo-resource` skill provides query capabilities for CloudRobo compute resources.
It covers two core areas: resource quota querying (with Domain-level aggregation and
CCE/ModelArts isolation) and resource pool querying (list with multi-condition filtering,
show with node-level details). This skill is read-only — no write operations are included.

**Applicable scenarios:**

- **Quota querying** — View workspace-level and Domain-level resource quotas; verify CCE
  (cpu/memory/gpu) and ModelArts (npu) quota isolation; check available capacity before
  launching workloads
- **Resource pool querying** — List resource pools by type/sub-type/pool-type/usages;
  inspect node-level details (name, status, resources, labels)

**Architecture:**

```
Agent / LLM
    │
    ├── CLI  →  cloudrobo resource <command>
    ├── SDK  →  ResourceClient (Python)
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/resources/quotas
              /v1/resources/pools
              /v1/resources/pools/{pool_id}
```

All operations target the `cloudrobo-service` backend. Resource operations are
domain-level — quota list and pool list require ABAC permission; pool detail does not.

## Prerequisites 前置条件

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
initial configuration. The `cloudrobo-resource` package depends on `cloudrobo-core`.
Ensure `cloudrobo workspace use --workspace-id <id>` has been run to set the active
workspace context before using resource commands.

## Workflow 工作流

### Quota Query Workflow 配额查询工作流

1. **List quotas** — `cloudrobo resource list-quotas` (returns domain_quotas + quotas + page_info)
2. **Filter by type** — `cloudrobo resource list-quotas --resource-type CCE` (CCE: npu=0; MODELARTS: cpu/memory/gpu=0)
3. **Filter by workspace** — `cloudrobo resource list-quotas --workspace-id <id>` (workspace-scoped quotas)
4. **Check capacity** — Review `domain_quotas[].available_spec` for available compute resources

### Resource Pool Query Workflow 资源池查询工作流

1. **List pools** — `cloudrobo resource list-pools` (returns resources + page_info)
2. **Filter pools** — `cloudrobo resource list-pools --resource-type MODELARTS --resource-sub-type STANDARD`
3. **Show pool detail** — `cloudrobo resource show-pool --pool-id <id>` (returns node info, status, config)

## CLI Command Format Standard CLI命令格式标准

```bash
cloudrobo resource <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Command group | `resource` | `cloudrobo resource` |
| Subcommand | kebab-case | `list-quotas`, `list-pools`, `show-pool` |
| Output format | JSON to stdout | `out(result)` |
| Comma list | `--usages TRAINING,INFERENCE` | `--usages TRAINING,INFERENCE` |
| Enum params | `click.Choice` validated | `--resource-type CCE|MODELARTS` |
| Pagination | `--limit 1-50` / `--offset N` | `--limit 20 --offset 0` |

## Core Commands 核心命令

### Quota Query 配额查询

#### List quotas

```bash
cloudrobo resource list-quotas [--workspace-id <id>] [--resource-id <id>] [--resource-type CCE|MODELARTS] [--resource-sub-type CPU|GPU|STANDARD|LITE] [--pool-type DEDICATED|SHARED] [--limit <n>] [--offset <n>] [--order ASC|DESC]
```

- **SDK:** `client.list_quotas(**params)`
- **API:** `GET /v1/resources/quotas`

Returns: `domain_quotas` (Domain-level aggregation with total_spec, used_spec,
available_spec), `quotas` (workspace-level list with quota_id, resource_name, specs,
nodes), `page_info`. CCE type quotas have `npu=0`; ModelArts type quotas have
`cpu/memory/gpu=0`.

### Resource Pool Query 资源池查询

#### List resource pools

```bash
cloudrobo resource list-pools [--resource-type CCE|MODELARTS] [--resource-sub-type CPU|GPU|STANDARD|LITE] [--pool-type DEDICATED|SHARED] [--usages TRAINING,INFERENCE] [--limit <n>] [--offset <n>] [--order ASC|DESC]
```

- **SDK:** `client.list_pools(**params)`
- **API:** `GET /v1/resources/pools`

Returns: `resources` (list of `ResourceVo` with resource_id, resource_name, resource_type,
resource_sub_type, nodes, config, status, description, usages, pool_type, create_at),
`page_info`. Pass `resource_id` to `show-pool --pool-id`.

#### Show resource pool detail

```bash
cloudrobo resource show-pool --pool-id <uuid>
```

- **SDK:** `client.show_pool(pool_id)`
- **API:** `GET /v1/resources/pools/{pool_id}`

`--pool-id` takes the pool's `resource_id` exactly as returned by `list-pools` — pass it
through unmodified (no prefix stripping needed).

Returns: full `ResourceVo` including `nodes` (name, status, resources,
available_resources, labels), `config`, `status` (AVAILABLE/UNAVAILABLE).

## Reference Documents 参考文档

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model and ABAC actions
- [API Paths](references/api-paths.md) — REST API paths discovered via SDK source
- [Resource Config Reference](references/resource-config-catalog.md) — Field mapping, validation rules, enums
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Verification Method](references/verification-method.md) — Verification method details
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria

## Edge Cases 边界情况

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Quota list returns all domain quotas; use `--workspace-id` to filter by workspace |
| ABAC permission denied (403) | Quota list and pool list require ABAC; pool detail does not require ABAC |
| Pagination out of range (400) | `limit` must be 1-50; `offset` must be ≥ 0; server validates and returns 400 |
| Resource pool not found (404) | `show-pool` with invalid `pool_id` returns 404; verify with `list-pools` first |
| AK/SK not set | Operations fail at HTTP signing step; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| API paths | Sourced from SDK source code (`_url()` calls in `client.py`), not inferred |
| Quota calculation isolation | CCE: only cpu/memory/gpu counted (npu=0); ModelArts: only npu counted (cpu/memory/gpu=0) |

## Verification Method 验证方法

### Specification Compliance Verification 规范合规验证

```bash
bash scripts/test-cli-commands.sh -s . -e cli
```

### Functional Testing 功能测试

```bash
# CLI / SDK
bash scripts/test-cli-commands.sh -s . -e {cli|sdk}
```

### Test Cases 测试用例

See `templates/test-vars.json` for the full test case list covering quota querying
and resource pool querying scenarios.

### Verification Checklist 验证清单

- Verify `list-quotas` returns `domain_quotas` with CCE `npu=0` and ModelArts `cpu/memory/gpu=0`
- Verify `list-quotas` supports `--workspace-id` and `--resource-type` filtering
- Verify `list-pools` returns `resources` with `page_info`
- Verify `show-pool` returns node-level details including `labels`
- Verify `list-quotas` and `list-pools` support pagination (`--limit`, `--offset`)

## Best Practices 最佳实践

- Run `list-quotas` before launching workloads to verify available capacity
- Use `--resource-type` filter to verify CCE/ModelArts quota isolation
- Use `list-pools` with `--usages` filter to find pools suitable for specific workloads
- Run `show-pool` to inspect node-level details before allocating resources
- Check `domain_quotas[].available_spec` for Domain-level capacity overview
- Use pagination (`--limit`, `--offset`) to manage large result sets efficiently
