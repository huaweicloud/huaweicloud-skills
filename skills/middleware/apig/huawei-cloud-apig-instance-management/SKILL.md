---
name: huawei-cloud-apig-instance-management
description: >
  Manage Huawei Cloud APIG (API Gateway, dedicated instances) via hcloud CLI:
  instance lifecycle (create/list/delete), API groups, API create/update/delete,
  publish/offline, request throttling policies, and public ingress EIP binding,
  plus read-only diagnosis of public access (eip_address vs sl_domain) and the
  instance -> group -> API -> publish chain. Delete operations require explicit
  user confirmation; instance creation is a 5-15 minute async operation that
  must be polled until status == Running.
  Triggers include: APIG, API gateway, 网关, API 分组, API 管理, 流控策略,
  throttling, publish API, 发布 API, 下线 API, 实例管理, 公网访问, ingress EIP,
  API 网关排障, apig.
tags: [huawei-cloud, apig, api-gateway, throttling, api-management]
---

# Huawei Cloud APIG API Gateway Management

## Overview

This skill manages Huawei Cloud APIG (API Gateway) dedicated instances and their
resources through the `hcloud` CLI (KooCLI). It covers instance lifecycle
management, API groups, API create/update, batch publish/offline, request
throttling policies, and public ingress EIP binding, together with read-only
diagnosis of public access configuration and the publish chain.

**Capabilities (17 `huawei_*` actions):**

| Category | Level | Actions |
| ---------- | ------- | --------- |
| Query | R3 (read-only, auto) | `huawei_list_apig_instances`, `huawei_get_apig_instance`, `huawei_list_apig_api_groups`, `huawei_list_apig_apis`, `huawei_list_apig_throttling_policies` |
| Analyze | R3 (read-only, auto) | `huawei_analyze_apig_public_access`, `huawei_analyze_apig_publish_chain` |
| Manage | R2 (preview + confirm) | `huawei_create_apig_instance`, `huawei_add_apig_ingress_eip`, `huawei_create_apig_api_group`, `huawei_create_apig_api`, `huawei_update_apig_api`, `huawei_publish_apig_api`, `huawei_create_apig_throttling_policy` |
| Manage (delete) | R1 (preview + explicit confirm) | `huawei_delete_apig_instance`, `huawei_delete_apig_api`, `huawei_delete_apig_api_group` |

**NOT covered** by this skill (use the Huawei Cloud APIG console for these):
signature keys / app credentials, API plugins, ACL policies, domain binding,
API group update/rename, and any other APIG operations not listed above.
Requests for these operations must be declined explicitly.

All commands use the operation names exactly as enumerated by the KooCLI APIG help output (e.g. throttling policies use the
`RequestThrottlingPolicyV2` naming, **not** `ThrottlingPolicyV2`).

## Critical Warnings

| # | Trap | Why |
| --- | ------ | ----- |
| 1 | API group region-locked | An API group cannot move across regions. Create it in the target region from the start. |
| 2 | Throttling default is per-API | The default throttling policy applies per API. Use app-level quotas (`--app_call_limits`) for per-user limits. |
| 3 | CORS must be explicit | OPTIONS preflight fails until CORS is configured on the API (`--cors=true`). |
| 4 | `BASIC` spec has no public IP | Use `PROFESSIONAL` + `--loadbalancer_provider=elb` for public access (`lvs` is internal-only). |
| 5 | Instance creation takes 5-15 min | Long-running async operation. The final state is **Running** (NOT "SUCCESS"). Poll with `ListInstancesV2` and wait for `status == "Running"`. |
| 6 | `sl_domain` is from the API **Group** | NOT from the instance. Get it from `CreateApiGroupV2` / `ListApiGroupsV2` response. It is an internal-only domain and may NXDOMAIN from the public internet — for public access use the instance `eip_address`. |
| 7 | API / throttling policy names must NOT have hyphens | `[a-zA-Z0-9_]+` only. Hyphens cause regex validation failure (verified for `CreateRequestThrottlingPolicyV2` too, APIG.2011). |
| 8 | VPC params need prefix | `--vpc.name=<n>` / `--subnet.vpc_id=<id>` / `--security_group.name=<n>` with KooCLI 7.x. |
| 9 | `AddIngressEipV2` works only with `elb` provider | `AddEipV2` (without "Ingress") requires the `lvs` provider. Ingress bandwidth minimum is 5 Mbit/s. |

## Prerequisites

1. **hcloud CLI** installed and authenticated — see `references/cli-installation-guide.md`
2. **Authentication**: AK/SK via environment variables (`HUAWEI_ACCESS_KEY` /
   `HUAWEI_SECRET_KEY` or any `HUAWEI*`/`HW*` pair containing access/secret key)
   **or** a local KooCLI profile created with the `configure` command
3. **Region**: APIG is region-specific. Always pass `--cli-region={region}` (e.g. `cn-north-4`, `ap-southeast-1`); if omitted, the profile region is used.
4. **IAM permissions** — see `references/iam-policies.md` for least-privilege policies
5. Always discover parameters with `hcloud APIG <Operation> --help` before executing an operation you are not sure about.

## Workflow

```
1. Identify the target APIG instance (huawei_list_apig_instances / huawei_get_apig_instance)
2. Route by intent:
   ├── Query   → list instances / groups / APIs / throttling policies
   ├── Analyze → public access analysis (eip_address vs sl_domain), publish chain analysis
   ├── Manage  → create instance (poll to Running), add ingress EIP, create group/API,
   │             update API, publish API, create throttling policy (preview + confirm)
   └── Delete  → delete instance / API / API group (empty the group first — see Delete — API; preview + explicit confirm, never automatic)
3. Return results: read-only actions return the command JSON; mutations return the
   resource snapshot read back after the operation completes
```

## Core Commands

Command naming: operation names are taken verbatim from the KooCLI APIG help enumeration.
Service name `APIG` is shown in the CLI help (the KooCLI metadata directory is
lowercase `apig`; both forms are accepted).

### Query — Instances

`huawei_list_apig_instances` — list APIG instances and status (including `eip_address`):

```bash
# --limit / --offset are optional pagination filters (example values shown)
hcloud APIG ListInstancesV2 --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--cli-region` | Yes (auto) | Region, agent fills automatically |
| `--limit` | No | Items per page, default 20 (max 500) |
| `--offset` | No | Query offset (default 0) |
| `--status` | No | Filter by gateway status, e.g. `Running`, `Creating`, `Deleting` |

`huawei_get_apig_instance` — query a single instance detail:

```bash
# Narrow to a single instance: add --instance_id=<your_instance_id> (a UUID)
hcloud APIG ListInstancesV2 --cli-region={region} --instance_id={instance_id}
```

> **Empty result means NOT found:** `ListInstancesV2` returns
> `{"total": 0, "instances": []}` (exit 0, no error) when the instance does not
> exist. Report "实例不存在，请确认 instance_id" instead of treating it as a
> successful query.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | No | Gateway ID (pass it to narrow to one instance) |

### Query — API Groups

`huawei_list_apig_api_groups` — list API groups (response includes `sl_domain`):

```bash
hcloud APIG ListApiGroupsV2 --cli-region={region} --instance_id={instance_id} --limit=20
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--limit` / `--offset` | No | Pagination |
| `--name` / `--id` | No | Filter by group name / ID |

### Query — APIs

`huawei_list_apig_apis` — list APIs in an instance:

```bash
# --group_id={group_id} optionally filters to a single API group
hcloud APIG ListApisV2 --cli-region={region} --instance_id={instance_id} --limit=20
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--group_id` | No | Filter by API group ID |
| `--name` / `--id` | No | Filter by API name / ID |
| `--req_method` / `--req_uri` | No | Filter by method / URI |
| `--auth_type` | No | Filter by auth type (IAM/APP/NONE) |

### Query — Throttling Policies

`huawei_list_apig_throttling_policies` — list request throttling policies
(operation name per the KooCLI APIG help enumeration):

```bash
hcloud APIG ListRequestThrottlingPolicyV2 --cli-region={region} --instance_id={instance_id} --limit=20
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--name` / `--id` | No | Filter by policy name / ID |
| `--limit` / `--offset` | No | Pagination |

### Analyze — Public Access

`huawei_analyze_apig_public_access` — analyze whether an instance is publicly
reachable and what address to use:

```bash
hcloud APIG ListInstancesV2 --cli-region={region} --instance_id={instance_id} --cli-output=json
hcloud APIG ListApiGroupsV2 --cli-region={region} --instance_id={instance_id} --cli-output=json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Gateway ID |

Analysis rules: if `instances[].eip_address` is a valid IP the instance has a
public inbound entry — use it for public access. If it is null, the instance is
internal-only (`BASIC` spec or `lvs` provider). `sl_domain` from the API group
is internal-only (e.g. `*.apic.cn-north-4.huaweicloudapis.com`) and must NOT be
advertised as a public endpoint.

### Analyze — Publish Chain

`huawei_analyze_apig_publish_chain` — walk the instance -> group -> API ->
publish-state chain to locate where a published endpoint is broken:

```bash
hcloud APIG ListInstancesV2 --cli-region={region}
hcloud APIG ListApiGroupsV2 --cli-region={region} --instance_id={instance_id}
hcloud APIG ListApisV2 --cli-region={region} --instance_id={instance_id}
# Optional: add --group_id={group_id} to restrict the walk to a single API group
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Gateway ID |
| `--group_id` | No | Restrict to one API group |

Report which hop is missing (no instance / no group / no API / no `publish_id`),
and warn when `sl_domain` is used for public access instead of `eip_address`.

### Manage — Create Instance (async, poll to Running)

`huawei_create_apig_instance` — create a pay-per-use dedicated gateway.
The API is asynchronous: creation takes 5-15 minutes. Poll `ListInstancesV2`
until `status == "Running"`:

```bash
# Run as a single line (no line continuations); always check CreateInstanceV2 --help first
hcloud APIG CreateInstanceV2 --cli-region={region} --instance_name={instance_name} --spec_id={spec_id} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --loadbalancer_provider={loadbalancer_provider} --available_zone_ids.1={available_zone_id}
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_name` | No* | Gateway name (needed to identify the instance) |
| `--spec_id` | No* | `BASIC` (no public access) / `PROFESSIONAL` (public access with `elb`) |
| `--vpc_id` / `--subnet_id` | No* | VPC / subnet in the target region |
| `--security_group_id` | No* | Security group (create one first via the VPC service) |
| `--loadbalancer_provider` | No* | `elb` for public access, `lvs` for internal only |
| `--available_zone_ids.1` | No* | AZ code like `ap-southeast-3a` (NOT a UUID) |
| `--enterprise_project_id` | No | Required for enterprise accounts; use `"0"` for the default project |

*The current KooCLI metadata marks CreateInstanceV2 parameters optional, but the
APIG API rejects the request without `spec_id`, `vpc_id`, `subnet_id`,
`security_group_id`, `loadbalancer_provider` and `available_zone_ids` — always
pass them. **Always** check `CreateInstanceV2 --help` first to confirm
parameter names before building the command.

Polling loop after creation:

```bash
while true; do
  status=$(hcloud APIG ListInstancesV2 --cli-region={region} --instance_id={instance_id} --cli-output=json | jq -r '.instances[0].status')
  [ "$status" = "Running" ] && break
  echo "instance status: $status, waiting 60s..."; sleep 60
done
```

Terminal state is `Running` (NOT "SUCCESS"). States such as `CreateSuccess` are
intermediate and still mean the instance is being provisioned.

### Manage — Add Ingress EIP

`huawei_add_apig_ingress_eip` — enable public inbound access on an `elb`-provider
gateway (bandwidth minimum 5 Mbit/s):

```bash
# --bandwidth_charging_mode: bandwidth|traffic; --bandwidth_size: Mbit/s (min 5)
hcloud APIG AddIngressEipV2 --cli-region={region} --instance_id={instance_id} --bandwidth_charging_mode=bandwidth --bandwidth_size=5
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--bandwidth_charging_mode` | No | `bandwidth` or `traffic` |
| `--bandwidth_size` | No | Ingress bandwidth in Mbit/s (min 5) |

Verification after binding: `ListInstancesV2` `eip_address` may **not** appear
promptly (verified: still `null` 8 minutes after success) — do NOT rely on it as
the sole evidence. Confirm success via the `AddIngressEipV2` response/task
acceptance, a retry returning `APIC.7711` ("Public inbound access is enabled"),
or the EIP list in the APIG console. Works only with `elb`-provider instances.

### Manage — Create API Group

`huawei_create_apig_api_group` — create an API group:

```bash
# --remark={remark} is optional
hcloud APIG CreateApiGroupV2 --cli-region={region} --instance_id={instance_id} --name={name}
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--name` | Yes | Group name (3-255 chars, starts with letter/digit) |
| `--remark` | No | Description |

### Manage — Create API

`huawei_create_apig_api` — create an API in a group:

```bash
hcloud APIG CreateApiV2 --cli-region={region} --instance_id={instance_id} --group_id={group_id} --type={type} --name={name} --req_protocol={req_protocol} --req_method={req_method} --req_uri={req_uri} --auth_type={auth_type} --backend_type={backend_type}
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--group_id` | Yes | API group ID |
| `--type` | Yes | API type, e.g. `1` (public) |
| `--name` | Yes | API name — `[a-zA-Z0-9_]+` only, NO hyphens |
| `--req_protocol` | Yes | `HTTPS` / `HTTP` / `BOTH` |
| `--req_method` | Yes | `GET` / `POST` / `PUT` / `DELETE` / `PATCH` / `HEAD` / `OPTIONS` / `ANY` |
| `--req_uri` | Yes | Request URI, e.g. `/demo` |
| `--auth_type` | Yes | `IAM` / `APP` / `NONE` |
| `--backend_type` | Yes | `HTTP` / `MOCK` / `FUNCTION` / `VPC_CHANNEL`. **Known limitation (KooCLI 7.2.12, verified):** creating an HTTP-backend API via `CreateApiV2` fails with `APIG.2011 invalid req_protocol` for every reasonable parameter combination, while `MOCK`/`FUNCTION` backends succeed. If an HTTP backend is required, use the APIG console, or create the API with a `MOCK`/`FUNCTION` backend and switch it in the console. |
| `--backend_api.req_uri` / `--backend_api.req_method` / `--backend_api.url_domain` | No | Backend routing when `backend_type=HTTP` |
| `--cors` | No | Set `true` when CORS preflight is required |

### Manage — Update API

`huawei_update_apig_api` — modify an existing API (auth mode, path, backend, etc.):

```bash
hcloud APIG UpdateApiV2 --cli-region={region} --instance_id={instance_id} --group_id={group_id} --api_id={api_id} --type={type} --name={name} --req_protocol={req_protocol} --req_method={req_method} --req_uri={req_uri} --auth_type={auth_type} --backend_type={backend_type}
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--api_id` | Yes | API ID (from `ListApisV2`) |
| `--instance_id` / `--group_id` | Yes | Locate the API inside the gateway |
| remaining | Yes | Same required fields as `CreateApiV2` |

### Manage — Publish / Offline API

`huawei_publish_apig_api` — batch publish or take offline APIs
(operation is `BatchPublishOrOfflineApiV2`; `apis` is a 1-based array):

```bash
# 1) Get the real environment ID first: hcloud APIG ListEnvironmentsV2 --cli-region={region} --instance_id={instance_id}
# 2) --env_id is the environment ID (RELEASE is only the environment NAME and is NOT accepted); replace the example UUID with the real env_id
hcloud APIG BatchPublishOrOfflineApiV2 --cli-region={region} --instance_id={instance_id} --action=online --env_id=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 --apis.1=9c8f2d0a111122223333444455556666
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--action` | Yes | `online` (publish) / `offline` (take offline) |
| `--env_id` | Yes | Environment **ID** (NOT the name). Query it first with `hcloud APIG ListEnvironmentsV2 --cli-region={region} --instance_id={instance_id}` and use the returned `env_id` — the name `RELEASE` is rejected with APIG.3003. |
| `--apis.1` | Yes* | 1-based array of API IDs (max 1000). Or use `--group_id` instead. |
| `--group_id` | No | Publish/offline all APIs of a group (alternative to `apis`) |
| `--remark` | No | Description |

### Manage — Create Throttling Policy

`huawei_create_apig_throttling_policy` — create a request throttling policy
(operation name per the KooCLI APIG help enumeration):

```bash
hcloud APIG CreateRequestThrottlingPolicyV2 --cli-region={region} --instance_id={instance_id} --name={name} --time_unit={time_unit} --time_interval={time_interval} --api_call_limits={api_call_limits}
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--instance_id` | Yes | Gateway ID |
| `--name` | Yes | Policy name — `[a-zA-Z0-9_]+` only, NO hyphens (same constraint as API names, see Critical Warning 7) |
| `--time_unit` | Yes | `SECOND` / `MINUTE` / `HOUR` / `DAY` |
| `--time_interval` | Yes | Time interval in the unit |
| `--api_call_limits` | Yes | Max API calls within the interval |
| `--app_call_limits` | No | Per-app quota (use for per-user limits) |
| `--user_call_limits` / `--ip_call_limits` | No | Per-user / per-IP limits |
| `--enable_adaptive_control` | No | Adaptive throttling (default false) |

### Delete — Instance

`huawei_delete_apig_instance` — delete a dedicated gateway (**R1: explicit user
confirmation required before running**):

```bash
hcloud APIG DeleteInstancesV2 --cli-region={region} --instance_id={instance_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Gateway ID to delete |

### Delete — API

`huawei_delete_apig_api` — delete an API from a group (**R1: explicit user
confirmation required before running**):

```bash
# Note: DeleteApiV2 takes --api_id + --instance_id only (--group_id is NOT a
# parameter of this operation; verified against `hcloud APIG DeleteApiV2 --help`)
hcloud APIG DeleteApiV2 --cli-region={region} --instance_id={instance_id} --api_id={api_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Gateway ID |
| `--api_id` | Yes | API ID to delete (from `ListApisV2`) |

> An API group cannot be deleted while it still contains APIs (APIG.3415). Use
> this action to delete each API in the group first, then delete the group.

### Delete — API Group

`huawei_delete_apig_api_group` — delete an API group (**R1: explicit user
confirmation required before running**):

```bash
hcloud APIG DeleteApiGroupV2 --cli-region={region} --instance_id={instance_id} --group_id={group_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Gateway ID |
| `--group_id` | Yes | API group ID to delete |

> **The group must be empty first:** APIG rejects deleting a group that still
> contains APIs (`APIG.3415 The API group cannot be deleted because it contains
> APIs`). Delete all APIs in the group with `huawei_delete_apig_api`
> (`DeleteApiV2`) before deleting the group. Only after every API is gone does
> `DeleteApiGroupV2` succeed.

## Parameter Confirmation

- Every `huawei_*` command must be checked against `hcloud APIG <Operation> --help`
  before execution; parameter names in this skill were verified against KooCLI 7.2.12 output.
- Required vs optional: `--cli-region` is always passed (agent fills it). Project ID (`--project_id`) is resolved automatically from the profile or region parent project.
- Mutating actions (Manage R2 / Delete R1) require previewing the full command and
  obtaining user confirmation before execution; Delete R1 additionally requires an
  explicit confirmation that the resource will be permanently removed.

## KooCLI Command Format Standard

The generic invocation shape is `hcloud APIG <Operation> --cli-region=<region> [--key=value ...]`
— this is a **format description only**: `<...>` and `[...]` are placeholders, never executed verbatim.

| Feature | Description | Example |
| --------- | ------------- | --------- |
| Service name | `APIG` (CLI help display; metadata dir `apig`) | `hcloud APIG ListInstancesV2 --cli-region={region}` |
| Operation name | PascalCase, verified against the KooCLI APIG help output | `ListInstancesV2` |
| Region | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple param | `--key=value` | `--instance_id=xxx` |
| Indexed array param | `--key.N=value` (1-based) | `--apis.1=xxx` |
| Nested object param | `--key.sub=value` | `--backend_api.req_uri=/demo` |

## Reference Documents

- `references/cli-installation-guide.md` — KooCLI install & authentication
- `references/iam-policies.md` — least-privilege IAM policies for APIG
- `references/verification-method.md` — how to verify each action
- `references/dataflow-diagram.md` — Mermaid data flow diagrams
- `references/acceptance-criteria.md` — acceptance criteria for the skill

APIG documentation: https://support.huaweicloud.com/apig/