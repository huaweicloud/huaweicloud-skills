---
name: huawei-cloud-bcs-manage
description: |
  Query and manage Huawei Cloud BCS (Blockchain Service, 区块链服务) from one
  entry point. Read-only: list blockchain instances with status/version/charging
  details, instance detail, organization/peer nodes, channels, union members and
  invitations, specifications, quotas, creation/deployment status, asynchronous
  operation records, alerts and monitoring metrics. Write: download certificates
  and Fabric SDK configuration, create/freeze/unfreeze user certificates,
  create/delete channels, add/remove peers and organizations, create/update/delete
  instances, and handle union member invitations. Uses the huaweicloudsdkbcs
  Python SDK (KooCLI only exposes BCS when its local metadata cache holds the BCS
  service template, so this skill does not depend on KooCLI). Read-only commands
  never prompt; every write prints an impact preview and requires --confirm, and
  asynchronous results are reported through ListOpRecord. Never queries or
  modifies chaincode lifecycle (no BCS OpenAPI; use the console).
  Use when the user wants to list/inspect BCS instances, channels, organizations,
  peers, members, quotas, alerts or metrics (inventory, daily inspection,
  troubleshooting, cost review), or to change BCS resources: create or delete an
  instance, manage channels/peers/organizations, issue or revoke certificates,
  download SDK config, or accept/reject union invitations.
  Triggers include: "BCS", "blockchain service", "区块链", "区块链服务",
  "BCS 实例", "blockchain instance", "BCS channel", "通道", "联盟成员",
  "BCS 配额", "BCS 告警", "BCS 监控", "BCS 监控指标", "list BCS",
  "query blockchain", "查看区块链实例", "查询区块链通道", "查询链码 SDK 配置",
  "how many blockchain instances", "创建区块链实例", "删除区块链实例",
  "BCS channel management", "创建通道", "删除通道", "添加节点", "移除组织",
  "下载证书", "下载SDK配置", "冻结证书", "联盟邀请", "BCS manage".
tags:
  - huawei-cloud
  - bcs
  - blockchain
  - query
  - manage
  - monitoring
  - certificate
---

# Huawei Cloud BCS Manage Skill

## Overview

This skill is the single entry point for Huawei Cloud **BCS (Blockchain Service,
区块链服务)**: **read-only inspection** and **state-changing operations** live in
one script and one document.

Read-only coverage:

- instance inventory and per-instance detail
- organization and peer node information
- channels, union members and invitation notifications
- specifications, quotas and creation/deployment status
- asynchronous operation records
- alerts (current/history, optional statistics) and monitoring metrics

Write coverage:

- certificate and Fabric SDK configuration download
- certificate creation, freeze and unfreeze
- channel create/delete, peer add/remove, organization removal
- instance create/update/delete
- union member invitation, invitation cancellation, invitation handling and union quit

**Architecture:**

```text
Agent → scripts/bcs_manage.py → huaweicloudsdkbcs (SDK) → BCS v2 API
```

**Execution mode: SDK.** KooCLI exposes BCS only when the local KooCLI metadata
cache contains the BCS service template
(`~/.hcloud/metaRepo/template/bcs`); on a machine without that template
`hcloud BCS --help` returns `[USE_ERROR]Unsupported service: BCS.` (exit 0).
Because that availability is environment-dependent, this skill does not depend
on KooCLI and always uses the `huaweicloudsdkbcs` Python SDK. API paths below
were verified from the SDK's `_http_info` definitions.

| Feature | Method | API path |
|---------|--------|----------|
| Instance list | `list_blockchains` | `GET /v2/{project_id}/blockchains` |
| Instance detail | `show_blockchain_detail` | `GET /v2/{project_id}/blockchains/{blockchain_id}` |
| Organization nodes | `show_blockchain_nodes` | `GET /v2/{project_id}/blockchains/{blockchain_id}/nodes` |
| Channels | `list_blockchain_channels` | `GET /v2/{project_id}/blockchains/{blockchain_id}/channels` |
| Union members | `list_members` | `GET /v2/{project_id}/members` |
| Notifications | `list_notifications` | `GET /v2/{project_id}/notifications` |
| Specifications | `show_blockchain_flavors` | `GET /v2/{project_id}/blockchains/flavors` |
| Quotas | `list_quotas` | `GET /v2/{project_id}/quotas` |
| Creation status | `show_blockchain_status` | `GET /v2/{project_id}/blockchains/{blockchain_id}/status` |
| Operation records | `list_op_record` | `GET /v2/{project_id}/operation/record` |
| Alerts | `list_bcs_events` | `POST /v2/{project_id}/blockchains/{blockchain_id}/events` |
| Alert statistics | `list_bcs_events_statistic` | `POST /v2/{project_id}/blockchains/{blockchain_id}/events/statistic` |
| Instance metrics | `list_bcs_metric` | `POST /v2/{project_id}/blockchains/{blockchain_id}/metric/list` |
| Entity metrics | `list_entity_metric` | `POST /v2/{project_id}/blockchains/{blockchain_id}/entity/metric/list` |
| Node metrics | `list_instance_metric` | `POST /v2/{project_id}/blockchains/{blockchain_id}/entity/instance/metric/list` |
| Download certificates | `download_blockchain_cert` | `GET /v2/{project_id}/blockchains/{blockchain_id}/cert` |
| Download SDK config | `download_blockchain_sdk_config` | `POST /v2/{project_id}/blockchains/{blockchain_id}/sdk-cfg` |
| Create user certificate | `create_blockchain_cert_by_user_name` | `POST /v2/{project_id}/blockchains/{blockchain_id}/orgs/{org_name}/usercert/{user_name}` |
| Freeze certificate | `freeze_cert` | `POST /v2/{project_id}/blockchains/{blockchain_id}/orgs/{org_name}/usercert/{user_name}/freeze` |
| Unfreeze certificate | `unfreeze_cert` | `POST /v2/{project_id}/blockchains/{blockchain_id}/orgs/{org_name}/usercert/{user_name}/unfreeze` |
| Create channels | `batch_create_channels` | `POST /v2/{project_id}/blockchains/{blockchain_id}/channels` |
| Add peers to channel | `batch_add_peers_to_channel` | `POST /v2/{project_id}/blockchains/{blockchain_id}/channels/peers` |
| Remove peers | `batch_remove_peers_from_channel` | `PUT /v2/{project_id}/blockchains/{blockchain_id}/{channel_id}/peers/quit` |
| Remove organizations | `batch_remove_orgs_from_channel` | `PUT /v2/{project_id}/blockchains/{blockchain_id}/{channel_id}/orgs/quit` |
| Delete channel | `delete_channel` | `DELETE /v2/{project_id}/blockchains/{blockchain_id}/channel/{channel_id}` |
| Create instance | `create_new_blockchain` | `POST /v2/{project_id}/blockchains` |
| Update instance | `update_instance` | `PUT /v2/{project_id}/blockchains/{blockchain_id}` |
| Delete instance | `delete_blockchain` | `DELETE /v2/{project_id}/blockchains/{blockchain_id}` |
| Invite members | `batch_invite_members_to_channel` | `POST /v2/{project_id}/members/invitations` |
| Cancel invitation | `delete_member_invite` | `DELETE /v2/{project_id}/members/invitations` |
| Handle invitation | `handle_notification` | `POST /v2/{project_id}/notification/handle` |
| Quit union | `handle_union_member_quit_list` | `PUT /v2/{project_id}/members/quit` |

**Execution-quality reporting:** every run reports trace_id, status
(`success` / `biz_fail` / `sys_fail`), error code and cost through the external
`skill-quality-cli` wrapper that invokes the script (see Core Commands; installed
by `scripts/ensure_cli.sh` if absent). Reporting is non-blocking and never
changes the result.

> **Capability boundary (能力边界):**
> **Chaincode (链码) has no BCS OpenAPI.** Chaincode names are only accepted as
> inputs when downloading the SDK configuration (`chaincode_name` /
> `channel_chaincode`). Lifecycle operations (install/instantiate/upgrade
> chaincode) must be done in the BCS console **链码管理** page; this skill
> cannot perform them.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

| Item | Requirement |
|------|-------------|
| Python | 3.8 or newer; verify with `python3 --version` |
| SDK | `pip install huaweicloudsdkbcs`. This skill is SDK-mode: it calls the Python SDK directly and does **not** require KooCLI |
| Credentials | `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY` accepted as fallbacks). The script only checks that they are present and never prints their values |
| Region | Default `cn-north-4`; override with `--region`. This is this skill's flag, **not** KooCLI's `--cli-region` |
| IAM permission | Read actions need `BCS ReadOnlyAccess`; write actions need the corresponding create/update/delete BCS permissions (or `BCS FullAccess`). See [IAM Policies](references/iam-policies.md) |
| KooCLI (optional) | `hcloud BCS` is usable only when the local metadata cache holds the BCS service template (`~/.hcloud/metaRepo/template/bcs`). Without that cache this skill runs on the SDK alone |

**Region flag note (SDK vs KooCLI):** `scripts/bcs_manage.py` always takes
`--region`; never pass `--cli-region` to it. `--cli-region` belongs to KooCLI
only. Equivalent commands:

```bash
# KooCLI form — available only when the BCS service template is cached locally
hcloud BCS ListBlockchains --cli-region=cn-north-4
# This skill's equivalent command (SDK mode)
python3 scripts/bcs_manage.py list --region=cn-north-4 --json
```

## Quick Start

1. Install the SDK (Python 3.8+): `pip install huaweicloudsdkbcs`.
2. Export `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` and choose a region
   (`--region`, default `cn-north-4`).
3. Run `bash scripts/ensure_cli.sh` once to install `skill-quality-cli`
   (idempotent; disable telemetry with `SKILL_QUALITY_REPORT=0`).

All commands use the single entry point `python3 scripts/bcs_manage.py
<subcommand>`. See [Prerequisites](#prerequisites) for the IAM policies and the
optional KooCLI note.

## Core Commands

### Read-Only Commands

Read-only subcommands never require `--confirm`. They print human-readable
tables by default; add `--json` for exactly one structured JSON payload on
stdout (progress/warnings go to stderr).

| Subcommand | Purpose | Key parameters |
|------------|---------|----------------|
| `list` | List instances with status/version/charging/cluster details | `--no-detail`, `--workers` |
| `detail` | One instance: basic info, channels, peer orgs, orderer, components | `--blockchain-id` / `--name` |
| `nodes` | Organization → peer node name / IP:port / channels | `--blockchain-id` / `--name` |
| `channels` | Channels of an instance | `--blockchain-id` / `--name` |
| `members` | Union members (invitor/invitee instances and tenants) | — |
| `notifications` | Union invitation notifications | — |
| `flavors` | Enterprise specification limits | `--limit`, `--offset` |
| `quotas` | Resource quota / used / free / min / max | — |
| `status` | Creation/deployment status per component | `--blockchain-id` / `--name` |
| `op-record` | Asynchronous operation records | `--blockchain-id`, `--operation-id`, `--operation-status`, `--operation-type`, `--resource-type` |
| `alerts` | Alerts/events for the window | `--blockchain-id` / `--name`, `--statistics`, `--type`, `--time-range`, `--step`, `--search`, `--order-by`, `--order`, `--max-points` |
| `metrics` | Monitoring metrics | `--blockchain-id` / `--name`, `--scope=instance\|entity\|node`, `--metric-names`, `--entity-name`, `--instance-name`, `--max-points` |

The granular aliases `events`, `events-statistic`, `metric`, `entity-metric` and
`instance-metric` remain available for compatibility.

#### Instance inventory and detail

```bash
# List instances; id/name come from ListBlockchains, other columns are
# enriched per instance via ShowBlockchainDetail (N+1 calls, concurrent).
python3 scripts/bcs_manage.py list --region={region} [--no-detail] [--workers=4] [--json]

# Instance detail by id or by name (name is resolved to a unique id)
python3 scripts/bcs_manage.py detail --region={region} --blockchain-id={blockchain_id}
python3 scripts/bcs_manage.py detail --region={region} --name={instance_name}

# Organization and peer node information
python3 scripts/bcs_manage.py nodes --region={region} --blockchain-id={blockchain_id}

# Channels of an instance
python3 scripts/bcs_manage.py channels --region={region} --blockchain-id={blockchain_id}
```

When the account has no instances, `list` prints
`No BCS instances found in this region.` and exits 0; a sample output table is
in [Example Requests](references/example-requests.md).

#### Union members and invitations

```bash
python3 scripts/bcs_manage.py members --region={region} [--json]
python3 scripts/bcs_manage.py notifications --region={region} [--json]
```

#### Specifications, quotas and status

```bash
python3 scripts/bcs_manage.py flavors --region={region} [--limit={limit}] [--offset={offset}]
python3 scripts/bcs_manage.py quotas --region={region}
python3 scripts/bcs_manage.py status --region={region} --blockchain-id={blockchain_id}
```

#### Asynchronous operation records

```bash
python3 scripts/bcs_manage.py op-record --region={region} \
  [--blockchain-id={blockchain_id}] [--operation-id={operation_id}] \
  [--operation-status={waiting|processing|finished|failed|stop}] \
  [--operation-type={operation_type}] [--resource-type={resource_type}]
```

#### Alerts and monitoring

```bash
# Alerts; default window is the last 60 minutes ("-1.-1.60")
python3 scripts/bcs_manage.py alerts --region={region} --blockchain-id={blockchain_id} \
  [--type={active_alert|history_alert}] [--time-range=-1.-1.60] [--step={step_ms}] \
  [--search={keyword}] [--order-by={fields}] [--order={asc|desc}] \
  [--max-points=10] [--json]

# Aggregated alert statistics for the same window
python3 scripts/bcs_manage.py alerts --region={region} --blockchain-id={blockchain_id} \
  --statistics [--type={active_alert|history_alert}] [--time-range=-1.-1.60] [--max-points=10] [--json]

# Instance metrics (default metric set = first five BCS metrics:
# cpuUsage, diskUsedRate, memUsedRate, sendBytesRate, recvBytesRate)
python3 scripts/bcs_manage.py metrics --region={region} --blockchain-id={blockchain_id} \
  [--scope=instance] [--metric-names=cpuUsage,diskUsedRate,memUsedRate] [--max-points=10] [--json]

# Organization / plugin metrics
python3 scripts/bcs_manage.py metrics --region={region} --blockchain-id={blockchain_id} \
  --scope=entity [--type={org|plugin}] [--entity-name={entity_name}] [--max-points=10] [--json]

# Single node (pod) metrics
python3 scripts/bcs_manage.py metrics --region={region} --blockchain-id={blockchain_id} \
  --scope=node --entity-name={org_name} [--instance-name={pod_name}] [--type={org|plugin}] \
  [--max-points=10] [--json]
```

**Metric time window:** the BCS metric APIs have no time-window field. The
`metrics` / `metric` / `entity-metric` / `instance-metric` subcommands accept
`--time-range` for CLI consistency but do **not** transmit it; BCS applies its
own server-side default window and a `WARNING` is printed. `--max-points` still
bounds the printed points. Alerts (`alerts` / `events` / `events-statistic`) do
honor `--time-range`.

### Write Commands

Every write subcommand prints an impact preview. Without `--confirm` the script
only prints the preview and exits with code **2**, changing nothing. Irreversible
actions (delete instance, delete channel, remove peers/orgs, freeze certificate)
are marked in the preview.

```bash
# General shape
python3 scripts/bcs_manage.py <subcommand> --region={region} <target/body flags> --confirm
```

#### Certificates and SDK configuration

- **download-cert** — download instance/organization certificates (binary).
  Required: `--blockchain-id`, `--org-name`, `--cert-type`; optional `--out`.
  Impact: writes private key material to disk with mode `0600`.
  ```bash
  python3 scripts/bcs_manage.py download-cert --region={region} \
    --blockchain-id={blockchain_id} --org-name={org_name} \
    --cert-type={cert_type} [--out={file_path}] --confirm
  ```
- **download-sdk-config** — download the Fabric SDK configuration (binary).
  Required: `--blockchain-id`, `--body-file`; optional `--out`.
  Impact: same sensitive-artifact handling as certificates.
  ```bash
  python3 scripts/bcs_manage.py download-sdk-config --region={region} \
    --blockchain-id={blockchain_id} --body-file={sdk_config.json} [--out={file_path}] --confirm
  ```
- **create-cert** — create a user certificate.
  Required: `--blockchain-id`, `--org-name`, `--user-name`; optional
  `--security-mode={true|false}`. Impact: issues a certificate for the user.
  ```bash
  python3 scripts/bcs_manage.py create-cert --region={region} \
    --blockchain-id={blockchain_id} --org-name={org_name} \
    --user-name={user_name} [--security-mode={true|false}] --confirm
  ```
- **freeze-cert** / **unfreeze-cert** — revoke / restore a user certificate.
  Required: `--blockchain-id`, `--org-name`, `--user-name`.
  Impact: `freeze-cert` is irreversible in effect (the credential stops working).
  ```bash
  python3 scripts/bcs_manage.py freeze-cert --region={region} \
    --blockchain-id={blockchain_id} --org-name={org_name} \
    --user-name={user_name} --confirm

  python3 scripts/bcs_manage.py unfreeze-cert --region={region} \
    --blockchain-id={blockchain_id} --org-name={org_name} \
    --user-name={user_name} --confirm
  ```

#### Channels and organizations

- **create-channels** — batch create channels. Required: `--blockchain-id`,
  `--body-file`. Impact: adds channels to the instance.
  ```bash
  python3 scripts/bcs_manage.py create-channels --region={region} \
    --blockchain-id={blockchain_id} --body-file={channels.json} --confirm
  ```
- **add-peers** — add peers to channels. Required: `--blockchain-id`,
  `--body-file`. Impact: joins more peers to existing channels.
  ```bash
  python3 scripts/bcs_manage.py add-peers --region={region} \
    --blockchain-id={blockchain_id} --body-file={peers.json} --confirm
  ```
- **remove-peers** — remove peers of an organization from a channel. Required:
  `--blockchain-id`, `--channel-id`, `--org-name`, `--peers`. Impact:
  **irreversible**, peer data leaves the channel.
  ```bash
  python3 scripts/bcs_manage.py remove-peers --region={region} \
    --blockchain-id={blockchain_id} --channel-id={channel_name} \
    --org-name={org_name} --peers={count} --confirm
  ```
- **remove-orgs** — remove organizations from a channel. Required:
  `--blockchain-id`, `--channel-id`, `--org-names`. Impact: **irreversible**.
  ```bash
  python3 scripts/bcs_manage.py remove-orgs --region={region} \
    --blockchain-id={blockchain_id} --channel-id={channel_name} \
    --org-names={org1,org2} --confirm
  ```
- **delete-channel** — delete a channel. Required: `--blockchain-id`,
  `--channel-id`. Impact: **irreversible**, channel data is lost.
  ```bash
  python3 scripts/bcs_manage.py delete-channel --region={region} \
    --blockchain-id={blockchain_id} --channel-id={channel_name} --confirm
  ```

#### Instance lifecycle

- **create-instance** — create a BCS instance. Required: `--body-file`.
  Impact: **incurs charges**; provisioning takes minutes.
  ```bash
  python3 scripts/bcs_manage.py create-instance --region={region} \
    --body-file={instance.json} --confirm
  ```
- **update-instance** — add/remove organizations or scale nodes. Required:
  `--blockchain-id`, `--body-file`. Impact: `is_delete_org=true` removes an
  organization and its peers/channel data (**irreversible**); otherwise scales
  nodes.
  ```bash
  python3 scripts/bcs_manage.py update-instance --region={region} \
    --blockchain-id={blockchain_id} --body-file={update.json} --confirm
  ```
  `node_orgs` is the API's **object array** (`list[NodeOrgs]`), for example
  `{"node_orgs":[{"name":"org-2","node_count":2}],"is_delete_org":true}` — the
  preview prints `org-2(2 nodes)` and the delete-org impact note.
- **delete-instance** — delete a BCS instance. Required: `--blockchain-id`;
  optional `--delete-storage`, `--delete-obs`, `--delete-resource`,
  `--delete-ief`. Impact: **irreversible**, all instance data is lost.
  ```bash
  python3 scripts/bcs_manage.py delete-instance --region={region} \
    --blockchain-id={blockchain_id} \
    [--delete-storage] [--delete-obs] [--delete-resource] [--delete-ief] --confirm
  ```

#### Union invitations

- **invite-members** / **delete-invite** / **handle-notification** /
  **quit-union** — all take `--body-file`; invitations affect union membership.
  ```bash
  python3 scripts/bcs_manage.py invite-members --region={region} \
    --body-file={invite.json} --confirm

  python3 scripts/bcs_manage.py delete-invite --region={region} \
    --body-file={cancel_invite.json} --confirm

  python3 scripts/bcs_manage.py handle-notification --region={region} \
    --body-file={notification.json} --confirm

  python3 scripts/bcs_manage.py quit-union --region={region} \
    --body-file={quit.json} --confirm
  ```

#### Body File Schemas

`--body-file` accepts the JSON shape expected by the BCS SDK request body;
`update-instance` uses an **object array** for `node_orgs`
(`[{"name":"org-2","node_count":2}]`). Full schemas for every body-based command:
[Body File Schemas](references/body-file-schemas.md).

Never write passwords into the skill directory or a repository; pass them via
the body file on the local machine only.

## Safety and Confirmation

1. **Preview first** — every write prints
   `=== WRITE OPERATION PREVIEW (...) ===` or
   `=== IRREVERSIBLE OPERATION PREVIEW (...) ===` with the target ids and impact.
2. **Confirmation gate** — without `--confirm` no API mutation occurs and the
   script exits with code `2`; review the preview, then re-run with `--confirm`.
3. **Irreversible actions** — delete instance, delete channel, remove peers,
   remove organizations and freeze certificate cannot be undone; get explicit
   user approval naming the exact target.
4. **No auto-retry** — treat ListOpRecord `failed` / `stop` as failure, report
   `desc`/`message`, and never retry a destructive operation automatically.
5. **Sensitive artifacts** — certificates and SDK configuration carry private
   key material; they are written with mode `0600` and must never be committed
   or shared.
6. **Read-only isolation** — read-only subcommands never ask for `--confirm`
   and never call a create/update/delete SDK method.

> **Cost and data-loss warning:** creating an instance incurs charges. Deleting
> an instance, deleting a channel, and removing organizations/peers destroy
> data and may be irreversible.

## Parameter Confirmation

Common flags: `--region` (default `cn-north-4`), `--json`, `--confirm` (every
write), `--blockchain-id` / `--name`, `--body-file`, `--timeout`, `--no-wait`.
The complete parameter table is in
[Parameter Reference](references/parameter-reference.md).

## Error Codes

`C01`/`C02` = credential or client problems, `U01`–`U04` = input/permission
problems, `B01` = runtime or empty-download failure, `N03` = BCS API error.
The full code table with actions is in
[Error Codes](references/error-codes.md).

## Workflow

Clarify read vs write intent → inspect ids and state first → choose the region →
run the subcommand → for writes review the preview and get approval before
`--confirm` → report only after ListOpRecord is `finished` → never auto-retry a
destructive action. Full checklist: [Workflow](references/workflow.md).

## Reference Documents

- [IAM Policies](references/iam-policies.md) — read-only and write permissions, region scoping
- [Verification Method](references/verification-method.md) — how to verify read and write paths safely
- [Dataflow Diagram](references/dataflow-diagram.md) — read and write request flows
- [Acceptance Criteria](references/acceptance-criteria.md) — combined acceptance checklist
- [CLI Installation Guide](references/cli-installation-guide.md) — telemetry CLI and KooCLI notes
- [Body File Schemas](references/body-file-schemas.md) — JSON body shapes for every `--body-file` command
- [Error Codes](references/error-codes.md) — full error code table and corrective actions
- [Example Requests](references/example-requests.md) — typical read and write prompt/command pairs
- [Troubleshooting](references/troubleshooting.md) — symptom, cause and action table
- [Parameter Reference](references/parameter-reference.md) — complete CLI flag table
- [Workflow](references/workflow.md) — end-to-end read/write checklist

## Example Requests

Typical prompts and their commands (read, inspect, write) are collected in
[Example Requests](references/example-requests.md).

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `hcloud` reports unsupported service | Local KooCLI metadata cache lacks the BCS template | Use this SDK-mode skill instead. KooCLI can reach BCS only with the template cached: `hcloud BCS ListBlockchains --cli-region=cn-north-4`; this skill's equivalent is `python3 scripts/bcs_manage.py list --region=cn-north-4` |

All other symptoms (missing SDK, `ERROR[C01]`–`ERROR[U04]`, empty downloads,
operation-record polling) are covered in
[Troubleshooting](references/troubleshooting.md).