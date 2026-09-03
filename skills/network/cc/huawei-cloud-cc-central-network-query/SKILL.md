---
name: huawei-cloud-cc-central-network-query
description: Queries Huawei Cloud Cloud Connect (CC) Central Network resources via hcloud CLI. Covers central network instances (single + list), central network attachments (single + list, including ER route table and GDGW attachment types), and central network connections (single + list). No write operations. Use this skill when the user needs to inspect central network topology, check central network connection status, review attachment configurations, or audit central network deployment. Triggers: 中心网络, Central Network, CC Central Network, 中心网络实例, 中心网络附件, 中心网络连接, central network instance, central network attachment, central network connection, 查询中心网络, central network query.
tags: [huawei-cloud cc cloud-connect central-network query]
---

# Huawei Cloud CC Central Network Query

## Overview

This skill queries Huawei Cloud Cloud Connect (CC) **Central Network** resources using the hcloud CLI. Central Network is a core concept in Cloud Connect that enables global, centralized network architecture across regions and clouds.

**Scope:** Query only — no create, update, or delete operations.

**Resources covered:**

| Resource | List | Show |
|----------|------|------|
| Central Network Instance | ✅ `ListCentralNetworks` | ✅ `ShowCentralNetwork` |
| Central Network Attachment | ✅ `ListCentralNetworkAttachments` | ✅ `ShowCentralNetworkErRouteTableAttachment` / `ShowCentralNetworkGdgwAttachment` |
| Central Network Connection | ✅ `ListCentralNetworkConnections` | ✅ Via `ListCentralNetworkConnections --id.1` filter |

> **Note on attachments:** Central network attachments come in two types — **ER Route Table** and **GDGW**. There is no generic "show attachment" command; you must use the type-specific command based on the attachment type.

> **Note on connection show:** There is no dedicated `ShowCentralNetworkConnection` API. To query a single connection, use `ListCentralNetworkConnections` with the `--id.1` filter, or read the `connections` array embedded in the `ShowCentralNetwork` response.


**Out of Scope (不覆盖的能力):**

The following Central Network capabilities are **not** covered by this skill. If the user requests any of these, inform them clearly that the skill does not support it.

| Capability | Reason | Suggested Action |
|------------|--------|------------------|
| Policy management (策略管理) — create / apply / delete / list policies, query change set | Write operations + not in scope | Use hcloud CLI directly or a management skill |
| Quota query (配额查询) — `ListCentralNetworkQuotas` | Not in scope | Use `hcloud CC ListCentralNetworkQuotas` directly |
| Capability list query (能力查询) — `ListCentralNetworkCapabilities` | Not in scope | Use `hcloud CC ListCentralNetworkCapabilities` directly |
| Create / Update / Delete central network or attachments | Write operations | Use hcloud CLI directly or a management skill |
| Update central network connections | Write operation | Use hcloud CLI directly or a management skill |
| Tag management (标签管理) | Not in scope | Use hcloud CLI directly |

> **If a user asks for 策略查询 / 策略管理 / 配额查询 / 能力查询 / 标签管理**, tell them this skill does not cover these capabilities and suggest using the hcloud CLI directly.

## Prerequisites

1. **hcloud CLI** installed and authenticated. See `references/cli-installation-guide.md`.
2. **IAM permissions:** `cc:centralNetworks:list` and `cc:centralNetworks:get`. See `references/iam-policies.md`.
3. **Region:** Central Network is a global service — use any region where CC is available (e.g., `cn-north-4`).
4. **Domain ID:** Most commands require `--domain_id` (account ID). Obtain from IAM → My Credentials.

## Workflow

```
1. Identify the target central network (List → pick by name/id)
2. Query details as needed:
   ├── Instance details → ShowCentralNetwork
   ├── Attachments → ListCentralNetworkAttachments → Show by type
   └── Connections → ListCentralNetworkConnections → filter by id for single
```

## Core Commands

### 1. List Central Network Instances

```bash
hcloud CC ListCentralNetworks --cli-region={region} --domain_id={domain_id} [optional filters]
```

**Key parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes | Region, e.g., `cn-north-4` |
| `--domain_id` | Yes | Account ID |
| `--id.1` | No | Filter by instance ID (supports multiple: `--id.1=xxx --id.2=yyy`) |
| `--name.1` | No | Filter by name |
| `--limit` | No | Page size (1–2000) |
| `--marker` | No | Pagination marker |
| `--sort_key` | No | Sort field |
| `--sort_dir` | No | Sort direction (`asc` / `desc`) |
| `--enterprise_project_id.1` | No | Filter by enterprise project ID |

**Example:**

```bash
hcloud CC ListCentralNetworks --cli-region=cn-north-4 --domain_id=xxx --limit=10
```

### 2. Show Central Network Instance

```bash
hcloud CC ShowCentralNetwork --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id}
```

**Key parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes | Region |
| `--domain_id` | Yes | Account ID |
| `--central_network_id` | Yes | Central network ID |

**Example:**

```bash
hcloud CC ShowCentralNetwork --cli-region=cn-north-4 --domain_id=xxx --central_network_id=cn-xxx
```

> The response includes an embedded `connections` array with `CentralNetworkConnectionInfo` objects — useful for viewing all connections without a separate call.

### 3. List Central Network Attachments

```bash
hcloud CC ListCentralNetworkAttachments --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id} [optional filters]
```

**Key parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes | Region |
| `--domain_id` | Yes | Account ID |
| `--central_network_id` | Yes | Central network ID |
| `--attachment_instance_type.1` | No | Filter by type: `GDGW` or `ER_ROUTE_TABLE` |
| `--id.1` | No | Filter by attachment ID |
| `--name.1` | No | Filter by name |
| `--state.1` | No | Filter by state (`AVAILABLE`, `CREATING`, `FAILED`, etc.) |
| `--limit` | No | Page size (1–2000) |
| `--marker` | No | Pagination marker |

**Example:**

```bash
hcloud CC ListCentralNetworkAttachments --cli-region=cn-north-4 --domain_id=xxx --central_network_id=cn-xxx --limit=10
```

### 4. Show Central Network Attachment (by type)

There is no generic show-attachment command. Use the type-specific command based on the attachment type.

#### 4a. Show ER Route Table Attachment

```bash
hcloud CC ShowCentralNetworkErRouteTableAttachment --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id} --er_route_table_attachment_id={attachment_id}
```

#### 4b. Show GDGW Attachment

```bash
hcloud CC ShowCentralNetworkGdgwAttachment --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id} --gdgw_attachment_id={attachment_id}
```

**How to determine attachment type:** Run `ListCentralNetworkAttachments` first — the response includes `attachment_instance_type` (`GDGW` or `ER_ROUTE_TABLE`) and the corresponding attachment ID for each entry.

### 5. List Central Network Connections

```bash
hcloud CC ListCentralNetworkConnections --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id} [optional filters]
```

**Key parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes | Region |
| `--domain_id` | Yes | Account ID |
| `--central_network_id` | Yes | Central network ID |
| `--id.1` | No | Filter by connection ID (use this for "show single") |
| `--name.1` | No | Filter by name |
| `--state.1` | No | Filter by state |
| `--is_cross_region` | No | Filter cross-region connections (boolean) |
| `--bandwidth_type` | No | Filter by bandwidth type: `BandwidthPackage` or `TestBandwidth` |
| `--connection_type` | No | Filter by connection type |
| `--limit` | No | Page size (1–2000) |
| `--marker` | No | Pagination marker |

**Example:**

```bash
hcloud CC ListCentralNetworkConnections --cli-region=cn-north-4 --domain_id=xxx --central_network_id=cn-xxx --limit=10
```

### 6. Show Single Central Network Connection

No dedicated `ShowCentralNetworkConnection` API exists. Use the list command with an ID filter:

```bash
hcloud CC ListCentralNetworkConnections --cli-region={region} --domain_id={domain_id} --central_network_id={central_network_id} --id.1={connection_id}
```

**Alternative:** The `ShowCentralNetwork` response embeds a `connections` array containing `CentralNetworkConnectionInfo` objects — you can find the target connection there without a separate call.

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{region}` | Yes | Huawei Cloud region | `cn-north-4` |
| `{domain_id}` | Yes | Account ID (IAM → My Credentials) | `xxx` |
| `{central_network_id}` | Yes (for show/list attachments/connections) | Central network instance ID | `cn-xxx` |
| `{attachment_id}` | Yes (for show attachment) | Attachment ID (type-specific) | `xxx` |
| `{connection_id}` | Yes (for show single connection) | Connection ID | `xxx` |

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md)
- [IAM Policies](references/iam-policies.md)
- [Verification Method](references/verification-method.md)
- [Data Flow Diagram](references/dataflow-diagram.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
- [API Reference](references/api-reference.md)

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `CC` (Cloud Connect) | `CC` |
| Operation name | PascalCase | `ListCentralNetworks`, `ShowCentralNetwork` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--central_network_id=cn-xxx` |
| Indexed parameter | `--key.1=value1` | `--id.1=cn-xxx` |
