---
name: huawei-cloud-cc-gcb-query
description: "Queries Huawei Cloud Cloud Connect (CC) Global Connection Bandwidth (GCB) resources via hcloud CLI. Covers single GCB detail query (including bound instance info), GCB list query with filters, GCB tenant configuration query (size ranges, quotas, charge modes, supported services), and list of GCBs eligible for binding to a specific service type. No write operations. Use this skill when the user needs to inspect global connection bandwidth details, check GCB-bound instances, review GCB tenant configs and quotas, or find GCBs available for binding. Triggers include: 全域互联带宽, GCB, Global Connection Bandwidth, global-connection-bandwidth, 云连接带宽, CC带宽, bandwidth config, 绑定带宽, support binding bandwidth, gcb-query."
tags: [huawei-cloud cc cloud-connect gcb bandwidth query]
---

## Overview

Huawei Cloud Cloud Connect (CC) provides **Global Connection Bandwidth (GCB)** — a bandwidth resource that can be bound to various service instances (cloud connections, central networks, branch networks, global EIPs) to enable cross-region or cross-cloud connectivity.

This skill provides **read-only query capabilities** for four GCB-related operations:

| Operation | Description |
|-----------|-------------|
| Show GCB | Query a single GCB by ID — response includes bound instance information |
| List GCBs | Paginated list with rich filters (status, charge mode, binding service, instance, type, name, enterprise project) |
| GCB Tenant Configs | Query tenant-level configuration: size ranges, quotas, supported charge modes, supported services, bind limit, SLA levels |
| Support Binding GCBs | List GCBs eligible for binding to a specific service type (CC / GEIP / GCN / GSN), filtered by local/remote area |

All operations are query-only (GET). No create, update, or delete operations are performed.

## Out of Scope

本 skill 不覆盖以下 GCB 查询能力：

| 未覆盖能力 | 对应 API / CLI 命令 | 说明 |
|-----------|-------------------|------|
| 标签管理 | `ListGcbResourceTags`, `ListGcbTenantTags`, `BatchCreateGcbResourceTags` 等 | 请使用 `hcloud CC ListGcbResourceTags` 等 |
| 线路级别 | `ListGlobalConnectionBandwidthLineLevels` | 请使用 `hcloud CC ListGlobalConnectionBandwidthLineLevels` |
| 站点 | `ListGlobalConnectionBandwidthSites` | 请使用 `hcloud CC ListGlobalConnectionBandwidthSites` |
| 规格代码 | `ListGlobalConnectionBandwidthSpecCodes` | 请使用 `hcloud CC ListGlobalConnectionBandwidthSpecCodes` |
| 所有写操作 | `Create`/`Delete`/`Update`/`Associate`/`Disassociate` 等 | 本 skill 仅提供查询（GET）能力 |

## Prerequisites

1. **hcloud CLI** installed and authenticated. See `references/cli-installation-guide.md` for details.
2. **Huawei Cloud AK/SK** configured via environment variables or CLI profile:
   ```bash
   # Set AK/SK via secure prompt — never hardcode secrets in scripts
   read -rsp "Access Key ID: "     HUAWEI_ACCESS_KEY; echo
   read -rsp "Secret Access Key: " HUAWEI_SECRET_KEY; echo
   export HUAWEI_ACCESS_KEY HUAWEI_SECRET_KEY
   export HUAWEI_REGION="cn-north-4"
   ```
3. **IAM permissions** — The caller needs `CC ReadOnlyAccess` or equivalent. See `references/iam-policies.md` for least-privilege policy.
4. **Domain ID** — All CC GCB APIs require `--domain_id` (account ID). Obtain it from the console: IAM → My Credentials → Account ID.

## Workflow

```
1. Identify the query type (single GCB / list / tenant configs / support binding)
2. Obtain the domain_id (account ID from IAM → My Credentials)
3. For single query: provide --domain_id and --id (GCB instance ID)
4. For list query: provide --domain_id, optionally add filters
5. For tenant configs: provide --domain_id only
6. For support binding: provide --domain_id and --binding_service (required)
7. Execute the hcloud command and review the output
```

## Core Commands

All commands use the format:
```bash
hcloud CC <Operation> --cli-region=<region> --domain_id=<account_id> [additional params]
```

### 1. Query a Single Global Connection Bandwidth

Query GCB details by ID. The response includes the GCB's configuration and **bound instance information** (which cloud connections, central networks, or other service instances are bound to this GCB).

```bash
hcloud CC ShowGlobalConnectionBandwidth --cli-region=cn-north-4 --domain_id=<account_id> --id=<gcb_id>
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes | GCB instance ID (32–36 characters) |

**Key response fields:**

| Field | Meaning |
|-------|---------|
| `id` | GCB instance ID |
| `name` | GCB name |
| `size` | Bandwidth size (Mbit/s) |
| `type` | Bandwidth type: `TrsArea` (跨区), `Area` (大区), `SubArea` (区域), `Region` (城域) |
| `charge_mode` | Charge mode: `bwd` (按带宽), `95` (传统95), `95avr` (日95) |
| `admin_state` | Status: `NORMAL` or `FREEZED` |
| `binding_service` | Bound service type: `CC`, `GEIP`, `GCN`, `GSN` |
| `instances` | List of bound instances (cloud connections, central networks, etc.) |
| `local_area` | Local access point |
| `remote_area` | Remote access point |
| `enterprise_project_id` | Enterprise project ID |

### 2. List Global Connection Bandwidths

Paginated list with rich filtering options.

```bash
hcloud CC ListGlobalConnectionBandwidths --cli-region=cn-north-4 --domain_id=<account_id> \
  [--limit=10] [--marker=<marker>] \
  [--admin_state.1=NORMAL] \
  [--binding_service.1=CC] \
  [--charge_mode.1=bwd] \
  [--id.1=<gcb_id>] \
  [--instance_id.1=<instance_id>] \
  [--instance_type.1=CC] \
  [--name.1=<name>] \
  [--type.1=TrsArea] \
  [--enterprise_project_id.1=<ep_id>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker (use with limit) |
| `--admin_state.[N]` | No | Filter by status: `NORMAL` or `FREEZED` |
| `--binding_service.[N]` | No | Filter by bound service type: `CC`, `GEIP`, `GCN`, `GSN` |
| `--charge_mode.[N]` | No | Filter by charge mode: `bwd`, `95`, `95avr` |
| `--id.[N]` | No | Filter by GCB ID (supports multiple) |
| `--instance_id.[N]` | No | Filter by bound instance ID |
| `--instance_type.[N]` | No | Filter by bound instance type: `CC`, `GEIP`, `GCN`, `GSN` |
| `--name.[N]` | No | Filter by name (supports multiple) |
| `--type.[N]` | No | Filter by bandwidth type: `TrsArea`, `Area`, `SubArea`, `Region` |
| `--enterprise_project_id.[N]` | No | Filter by enterprise project ID |

### 3. Query GCB Tenant Configuration

Query tenant-level configuration for GCB — includes size ranges per charge mode, quotas, supported services, supported bandwidth types, bind limit, SLA levels, and more.

```bash
hcloud CC ListGlobalConnectionBandwidthConfigs --cli-region=cn-north-4 --domain_id=<account_id>
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |

**Key response fields:**

| Field | Meaning |
|-------|---------|
| `gcbSizeRange` / `size_range` | Bandwidth size ranges per charge mode (`trf`, `bwd`, `95p`, `95`, `95avr`) |
| `quotas` | Quotas: `gcb.size` (total bandwidth quota) and `gcb.count` (GCB count quota) |
| `charge_mode` / `chargeMode` | Supported charge modes |
| `services` / `serviceList` | Supported binding service types |
| `gcb_type` / `gcbType` | Supported GCB types: `Area`, `TrsArea`, `Region`, `SubArea` |
| `bind_limit` | Maximum number of instances that can be bound to a single GCB |
| `sla_level` | SLA levels: `Pt`, `Au`, `Ag` |
| `relation` | Which service types are supported per GCB type |
| `crossborder` | Whether cross-border bandwidth is enabled |
| `ces_enabled` | Whether CES monitoring is enabled |

### 4. List GCBs Eligible for Binding

List GCBs that meet binding conditions for a specific service type. Useful when you need to find an available GCB to bind to a new cloud connection, central network, or other service instance.

```bash
hcloud CC ListSupportBindingConnectionBandwidths --cli-region=cn-north-4 --domain_id=<account_id> \
  --binding_service=<CC|GEIP|GCN|GSN> \
  [--limit=10] [--marker=<marker>] \
  [--local_area=<local_area>] \
  [--remote_area=<remote_area>] \
  [--enterprise_project_id.1=<ep_id>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--binding_service` | Yes | Target service type: `CC` (cloud connection), `GEIP` (global EIP), `GCN` (central network), `GSN` (branch network) |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--local_area` | No | Local access point (use with `remote_area`; both must be present or both absent) |
| `--remote_area` | No | Remote access point (use with `local_area`) |
| `--enterprise_project_id.[N]` | No | Filter by enterprise project ID |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-4` |
| `--domain_id` | Yes | Account ID (from IAM → My Credentials) | `0a12345678...` |
| `--id` | Yes (Show) | GCB instance ID (32–36 char UUID) | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `--binding_service` | Yes (Support Binding) | Target service type | `CC` |
| `--limit` | No | Page size (1–2000) | `10` |
| `--marker` | No | Pagination token | `<marker from previous page>` |

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — hcloud CLI setup and authentication
- [IAM Policies](references/iam-policies.md) — Least-privilege policy for CC GCB query operations
- [Verification Method](references/verification-method.md) — How to verify query results
- [Data Flow Diagram](references/dataflow-diagram.md) — Mermaid diagram of skill data flow
- [Acceptance Criteria](references/acceptance-criteria.md) — Success criteria for each query type
- [API Reference](references/api-reference.md) — Verified REST API endpoints

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `CC` (Cloud Connect) | `CC` |
| Operation name | PascalCase | `ShowGlobalConnectionBandwidth`, `ListGlobalConnectionBandwidths` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--id=xxx` |
| Indexed array parameter | `--key.1=value1` | `--admin_state.1=NORMAL` |
