---
name: huawei-cloud-cc-instance-query
description: "Queries Huawei Cloud Cloud Connect (CC) resources via hcloud CLI. Covers cloud connection instances (single + list), bandwidth packages (single + list), inter-region bandwidths (single + list), network instances (single + list), cloud connection routes (single + list), and cross-account authorisations (granted + received). No write operations. Use this skill when the user needs to inspect cross-cloud connectivity topology, check bandwidth package status, review inter-region bandwidth allocation, query network instances attached to a cloud connection, troubleshoot routing in Cloud Connect, or audit cross-account authorisation relationships (who authorised whom). Triggers: 云连接, CC, Cloud Connect, 带宽包, bandwidth package, 域间带宽, inter-region bandwidth, 网络实例, network instance, 路由查询, cloud connection route, 跨云网络, cross-cloud connectivity, 授权, authorisation, 被授权, permission, 跨账号, cross-account."
tags: [huawei-cloud cc cloud-connect query authorisation]
---

## Overview

Huawei Cloud Cloud Connect (CC) is a service that enables cross-region and cross-cloud network connectivity. This skill provides **read-only query capabilities** for seven core CC resource types:

| Resource Type | Description |
|--------------|-------------|
| Cloud Connection | The top-level container that links VPCs across regions or clouds |
| Bandwidth Package | Purchased bandwidth resource bound to a cloud connection |
| Inter-Region Bandwidth | Bandwidth allocated between two specific regions within a bandwidth package |
| Network Instance | A VPC or VPC subnet attached to a cloud connection |
| Cloud Connection Route | Routing entries that direct traffic through the cloud connection |
| Authorisation (granted) | Cross-account authorisations this account has granted to others — "which of my network instances did I authorise other accounts to load?" |
| Permission (received) | Cross-account authorisations other accounts have granted to this account — "which foreign network instances can I load into my cloud connections?" |

All operations are query-only (GET). No create, update, or delete operations are performed.

## Out of Scope

This skill does **not** cover the following CC resource types and operations. If the user asks about these, inform them clearly and suggest the corresponding hcloud CLI command.

| Out-of-Scope Resource / Operation | Suggested Command |
|----------------------------------|-------------------|
| Central Network（中心网络） | `hcloud CC ListCentralNetworks` / `hcloud CC ShowCentralNetwork` |
| Global Connection Bandwidth（全局互联带宽/GCB） | `hcloud CC ListGlobalConnectionBandwidths` / `hcloud CC ShowGlobalConnectionBandwidth` |
| Site Network（站点网络） | `hcloud CC ListSiteNetworks` / `hcloud CC ShowSiteNetwork` |
| Tag management（标签管理: Tag/Untag/ListTags） | `hcloud CC ListTags` / `hcloud CC ListCloudConnectionTags` |
| All write operations（Create/Update/Delete/Apply/Associate/Disassociate） | Not supported — this skill is read-only |


## Prerequisites

1. **hcloud CLI** installed and authenticated. See `references/cli-installation-guide.md` for details.
2. **Huawei Cloud AK/SK** configured via `hcloud configure` (interactive, recommended) or environment variables:
   ```bash
   # Recommended: interactive configuration
   hcloud configure
   # Or set env vars: HUAWEI_ACCESS_KEY, HUAWEI_SECRET_KEY, HUAWEI_REGION
   ```
3. **IAM permissions** — The caller needs `CC ReadOnlyAccess` or equivalent. See `references/iam-policies.md` for least-privilege policy.
4. **Domain ID** — All CC APIs require `--domain_id` (account ID). Obtain it from the console: IAM → My Credentials → Account ID.

## Workflow

```
1. Identify the resource type to query (cloud connection / bandwidth package / inter-region bandwidth / network instance / route / authorisation / permission)
2. Determine whether a single instance or a list is needed
3. For single queries: provide --domain_id and --id
4. For list queries: provide --domain_id, optionally add filters (--limit, --marker, --status, --name, etc.)
5. Execute the hcloud command and review the output
6. **domain_id validation**: If `--domain_id` is not explicitly provided, the CLI will silently use the default domain_id from the auth config (not an error). Always recommend the user specify `--domain_id` explicitly to avoid querying the wrong account.
```

## Core Commands

All commands use the format:
```bash
hcloud CC <Operation> --cli-region=<region> --domain_id=<account_id> [additional params]
```

### 1. Cloud Connection Instances

**Query a single cloud connection:**
```bash
hcloud CC ShowCloudConnection --cli-region=cn-north-4 --domain_id=<account_id> --id=<cloud_connection_id>
```

**List cloud connections:**
```bash
hcloud CC ListCloudConnections --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--marker=<marker>] [--status.1=ACTIVE] [--name.1=<name>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes (Show) | Cloud connection instance ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker (use with limit) |
| `--status.[N]` | No | Filter by status (e.g., ACTIVE) |
| `--name.[N]` | No | Filter by resource name |
| `--id.[N]` | No | Filter by resource ID (list only) |
| `--enterprise_project_id.[N]` | No | Filter by enterprise project ID |

### 2. Bandwidth Package Instances

**Query a single bandwidth package:**
```bash
hcloud CC ShowBandwidthPackage --cli-region=cn-north-4 --domain_id=<account_id> --id=<bandwidth_package_id>
```

**List bandwidth packages:**
```bash
hcloud CC ListBandwidthPackages --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--status.1=ACTIVE] [--cloud_connection_id.1=<cc_id>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes (Show) | Bandwidth package instance ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--status.[N]` | No | Filter by status (e.g., ACTIVE) |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--billing_mode.[N]` | No | Filter by billing mode |

### 3. Inter-Region Bandwidth Instances

**Query a single inter-region bandwidth:**
```bash
hcloud CC ShowInterRegionBandwidth --cli-region=cn-north-4 --domain_id=<account_id> --id=<inter_region_bandwidth_id>
```

**List inter-region bandwidths:**
```bash
hcloud CC ListInterRegionBandwidths --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--cloud_connection_id.1=<cc_id>] [--bandwidth_package_id.1=<bp_id>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes (Show) | Inter-region bandwidth instance ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--bandwidth_package_id.[N]` | No | Filter by bandwidth package ID |

### 4. Network Instances

**Query a single network instance:**
```bash
hcloud CC ShowNetworkInstance --cli-region=cn-north-4 --domain_id=<account_id> --id=<network_instance_id>
```

**List network instances:**
```bash
hcloud CC ListNetworkInstances --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--cloud_connection_id.1=<cc_id>] [--region_id.1=<region>] [--status.1=ACTIVE]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes (Show) | Network instance ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--region_id.[N]` | No | Filter by deployment region |
| `--status.[N]` | No | Filter by status (e.g., ACTIVE) |
| `--type.[N]` | No | Filter by network instance type |

### 5. Cloud Connection Routes

**Query a single route:**
```bash
hcloud CC ShowCloudConnectionRoutes --cli-region=cn-north-4 --domain_id=<account_id> --id=<route_id>
```

**List routes:**
```bash
hcloud CC ListCloudConnectionRoutes --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--cloud_connection_id.1=<cc_id>] [--instance_id.1=<ni_id>] [--region_id=<region>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID |
| `--id` | Yes (Show) / No (List) | Route instance ID |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--instance_id.[N]` | No | Filter by network instance ID |
| `--region_id` | No (List only) | Filter by region ID |

### 6. Cross-Account Authorisations (Granted)

Use this to answer: **"Which of my network instances have I authorised other accounts to load into their cloud connections?"**

This is the **grantor's** view — the calling account owns the network instances and has authorised other accounts (identified by `cloud_connection_domain_id`) to load them.

**List authorisations:**
```bash
hcloud CC ListAuthorisations --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--cloud_connection_id.1=<cc_id>] [--instance_id.1=<ni_id>] [--id.1=<auth_id>] [--name.1=<name>] [--description.1=<desc>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID (the grantor — your account) |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--instance_id.[N]` | No | Filter by network instance ID |
| `--id.[N]` | No | Filter by authorisation ID |
| `--name.[N]` | No | Filter by authorisation name |
| `--description.[N]` | No | Filter by description |

**Key response fields:**

| Field | Meaning |
|-------|---------|
| `id` | Authorisation record ID |
| `domain_id` | The grantor's domain ID (your account) |
| `instance_id` | The network instance being authorised |
| `instance_type` | Network instance type (e.g., `vpc`) |
| `cloud_connection_id` | The cloud connection that will load the instance |
| `cloud_connection_domain_id` | The grantee's domain ID (the other account) |
| `is_loaded_by_cloud_connection` | Whether the grantee has actually loaded the instance into the cloud connection |
| `status` | Authorisation status (e.g., `authorized`) |

### 7. Cross-Account Permissions (Received)

Use this to answer: **"Which foreign network instances have other accounts authorised me to load into my cloud connections?"**

This is the **grantee's** view — the calling account owns the cloud connections and can load network instances owned by other accounts (identified by `instance_domain_id`).

**List permissions:**
```bash
hcloud CC ListPermissions --cli-region=cn-north-4 --domain_id=<account_id> [--limit=10] [--cloud_connection_id.1=<cc_id>] [--instance_id.1=<ni_id>] [--id.1=<perm_id>] [--name.1=<name>] [--description.1=<desc>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain_id` | Yes | Account ID (the grantee — your account) |
| `--limit` | No | Records per page (1–2000) |
| `--marker` | No | Pagination marker |
| `--cloud_connection_id.[N]` | No | Filter by cloud connection ID |
| `--instance_id.[N]` | No | Filter by network instance ID |
| `--id.[N]` | No | Filter by permission ID |
| `--name.[N]` | No | Filter by permission name |
| `--description.[N]` | No | Filter by description |

**Key response fields:**

| Field | Meaning |
|-------|---------|
| `id` | Permission record ID |
| `domain_id` | The grantee's domain ID (your account) |
| `instance_id` | The foreign network instance authorised to you |
| `instance_type` | Network instance type (e.g., `vpc`) |
| `instance_domain_id` | The grantor's domain ID (the other account that owns the instance) |
| `cloud_connection_id` | Your cloud connection that can load the instance |
| `status` | Permission status (e.g., `authorized`) |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-4` |
| `--domain_id` | Yes | Account ID (from IAM → My Credentials) | `0a12345678...` |
| `--id` | Yes (Show ops) | Resource instance ID (32–36 char UUID) | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `--limit` | No | Page size (1–2000) | `10` |
| `--marker` | No | Pagination token | `<marker from previous page>` |

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — hcloud CLI setup and authentication
- [IAM Policies](references/iam-policies.md) — Least-privilege policy for CC query operations
- [Verification Method](references/verification-method.md) — How to verify query results
- [Data Flow Diagram](references/dataflow-diagram.md) — Mermaid diagram of skill data flow
- [Acceptance Criteria](references/acceptance-criteria.md) — Success criteria for each query type
- [API Reference](references/api-reference.md) — Verified REST API endpoints from SDK source

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `CC` (Cloud Connect) | `CC` |
| Operation name | PascalCase | `ShowCloudConnection`, `ListCloudConnections` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--id=xxx` |
| Indexed array parameter | `--key.1=value1` | `--status.1=ACTIVE` |
