---
name: huawei-cloud-computing-query
description: |
  Queries Huawei Cloud computing resources (ECS/BMS/IMS/AS/CCE), Covers ECS instances, flavors, keypairs, quotas, server groups, block devices, NICs, VNC console, BMS bare metal servers/flavors/quotas, IMS images/OS versions/members/quotas, AS scaling groups/configs/policies/activity logs/lifecycle hooks/warm pools/quotas, and CCE clusters/nodes/node pool details/node pool tags/cluster tags/quotas (read-only). No write operations. Cross-category: for cloud disks (EVS) use the storage query skill; for ECS create/start/stop/reboot/delete/resize use the ECS management skill; for CCE workloads/namespaces/events use the CCE kubectl-based skills. Use this skill when the user needs to query ECS instance details, list flavors, check BMS availability, browse images, view auto-scaling group/policy status, or inventory CCE clusters and nodes. Triggers include: "弹性云服务器", "ECS", "裸金属", "BMS", "镜像", "IMS", "弹性伸缩", "AS", "伸缩组", "伸缩策略", "规格查询", "CCE", "云容器引擎", "集群", "节点", "节点池", "flavor", "instance", "image", "scaling", "cluster", "node".
triggers: [弹性云服务器, ECS, 裸金属, BMS, 镜像, IMS, 弹性伸缩, AS, 伸缩组, 伸缩策略, 规格查询, CCE, 云容器引擎, 集群, 节点, 节点池, flavor, instance, image, scaling, cluster, node]
---
# Huawei Cloud Resource Query

> **Execution method: this skill runs local Python scripts against the Huawei Cloud SDK. `hcloud`,
> `openstack`, `curl` and hand-written API calls are not execution paths for this skill.**
>
> Run every query from the skill directory with the venv Python created by the environment check:
> `.venv/bin/python3 scripts/huawei_<service>.py <subcommand> [options]`
> (Windows: `.venv\Scripts\python.exe`). When the host provides a `skill action=exec` tool, prefix the
> same command with `skill action=exec:` and use `skill://` paths.
>
> The entry scripts are executable (`chmod +x`, shebang `#!/usr/bin/env python3`), so
> `scripts/huawei_<service>.py <subcommand>` also runs directly; `-h` works on a bare host with neither
> SDK nor credentials, and both entry forms resolve the same options.

## Overview

Read-only query skill for Huawei Cloud computing resources, available specifications and existing
resource inventory. In scope: resource lists and details, selection data (flavors, images, AZs,
quotas), resource IDs and dependencies. Out of scope: creating, modifying, deleting, resizing,
reinstalling or restarting any resource; guessing data that was not queried.

## Services and entries

| Category | Service | Entry | Guide |
|----------|---------|-------|-------|
| ECS | Elastic Cloud Server | `scripts/huawei_ecs.py` | `references/ecs/guide.md` |
| BMS | Bare Metal Server | `scripts/huawei_bms.py` | `references/bms/guide.md` |
| IMS | Image Management Service | `scripts/huawei_ims.py` | `references/ims/guide.md` |
| AS | Auto Scaling | `scripts/huawei_as.py` | `references/as/guide.md` |
| CCE | Cloud Container Engine | `scripts/huawei_cce.py` | `references/cce/guide.md` |

Each entry exposes one subcommand per operation. The subcommand name equals the old script file name
without the `.py` suffix; for example `scripts/huawei_ecs.py list_servers_details`.

## Usage principles

1. This skill only queries; it never creates, modifies or deletes resources.
2. Prefer the region, project, AZ, resource name and resource ID supplied by the user.
3. Query exactly one region per call. Do not silently loop over regions; for a multi-region view,
   confirm the region list first and label each result block.
4. Base every answer on actual API responses; never speculate from experience.
5. Preserve key fields in the answer so they can be reused (IDs, names, specifications, images).
6. Narrow large result sets with `--name`, `--id`, `--status`, `--tag` or `--limit`.
7. If a resource type has no subcommand in the matching guide, say so instead of returning unreliable data.
8. Run `-h` on a subcommand before using it; the help page lists every accepted parameter.
9. Do not fabricate subcommand names; use only the names listed in the guide.

## Prerequisites

Run the environment check once per session. A passing result is cached for 30 minutes in
`.env_check_cache`, so repeated calls are cheap.

```bash
bash scripts/check_env.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_env.ps1
```

The check runs light credential and Python checks first, then dependency, SDK and service checks.
Missing credentials fail fast with exit code 2; a host with credentials but unreachable package
mirrors or network fails with exit code 3 and a readable hint. The first run may create a virtual
environment and install the SDK packages, which can take tens of seconds; the whole run is bounded by
a total timeout (`HW_ENV_CHECK_TIMEOUT`, default 120 seconds) so it never waits silently. Force a
re-check with `--force` or `HW_ENV_CHECK_FORCE=1`; change the cache TTL with `--ttl <seconds>` or
`HW_ENV_CHECK_TTL`.

Quick self-check without installing dependencies: run `-h` on any entry script, for example
`.venv/bin/python3 scripts/huawei_ecs.py list_servers_details -h`. Help handling happens before the
credential and SDK checks, so it exits 0 and prints the accepted parameters even on a bare host. Use it
to confirm the skill is executable before spending time on the full environment check.

Environment variables (values are secrets; never echo them):

- `HW_ACCESS_KEY` / `HW_SECRET_KEY` — required AK/SK
- `HW_REGION_NAME` — optional, default `cn-north-4`; fallback for every `--region`
- `HW_PROJECT_ID` — optional project ID; otherwise resolved once through IAM and reused
- `HW_SECURITY_TOKEN` — optional, required only for temporary AK/SK

## Workflow

1. Run the environment check once at the start of the session.
2. Read the matching guide under `references/<service>/` and choose a subcommand.
3. Run the subcommand's `-h` page to confirm parameters.
4. Execute the query with the skill venv Python.
5. Summarize the result using the presentation rules below.

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_cce.py list_nodes --region cn-north-4 --cluster_id "<cluster_id>" --all
```

## Core Commands

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details -h
```

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_flavors --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_ims.py list_images --region cn-north-4 --os_type Linux --limit 20
```

## Parameter Confirmation

| Parameter | Required | Description |
|-----------|----------|-------------|
| subcommand | yes | Operation name from the matching guide, e.g. `list_servers_details` |
| `--region` | no | Region; falls back to `HW_REGION_NAME` (default `cn-north-4`) |
| `--project_id` | no | Project ID; resolved once through IAM when omitted |
| `--limit` | no | Rows displayed by list subcommands, default 20 |
| `--all` | no | Walk every page and display all rows |
| `--fields` | no | Comma-separated display fields, e.g. `id,name,status` |
| `--json` | no | Raw JSON output |
| resource ID flags | depends | Required by show subcommands, e.g. `--server_id`, `--cluster_id` |

## Output and cost controls

- List subcommands print `id`, `name`, `status` by default, at most 20 rows, plus `共 N 条，当前返回 M 条`.
- `--limit <n>` changes displayed rows; `--all` walks every page; `--fields` selects columns.
- `--json` prints raw rows; `--project_id` is resolved once per process and reused.
- Show subcommands print `field: value` lines; use `--fields` to keep the answer compact.
- Empty results include the region and a short diagnostic hint instead of an empty table.
- Full pagination and trimming contract: `references/verification-method.md`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | success, or `-h` / `--help` |
| 2 | missing credentials or a missing required parameter |
| 3 | SDK missing, network failure, or an API error |

`-h` is handled before credential validation, so it always works on a bare host.

## Related skills

| User intent | Entry point |
|-------------|-------------|
| Query ECS / BMS / IMS / AS / CCE (read-only) | **this skill** |
| ECS lifecycle change (create/start/stop/reboot/delete/resize) | ECS management skill (write path) |
| ECS reinstall OS | ECS console, or KooCLI outside this skill |
| Cloud disks, snapshots, EVS quotas; OBS buckets / objects | Storage query skill |
| CCE workloads, namespaces, events, pod logs | `container/cce/` kubectl-based skills |
| CCE metrics; CCE add-ons and node pool resize (write) | CCE metrics and cluster management skills |
| RDS instances / databases | RDS query skill |
| SWR instances / repositories; VOD resources | SWR / VOD query skills |
| DeH / dedicated host | Not covered yet; use the console |

When a request crosses the read-only boundary, name the owning skill and stop; do not attempt a write
with this skill. See `references/cli-installation-guide.md` for the KooCLI boundary.

## Verification

1. Run the environment check to confirm dependencies and credentials.
2. Run `-h` on the chosen subcommand to confirm parameters.
3. Query a known resource and compare id / name / status with the console.
4. Check that the returned total is reasonable.
5. Complete offline and live checklist: `references/verification-method.md`.

## Reference Documents

- `references/ecs/guide.md` — ECS subcommands, parameters and examples
- `references/bms/guide.md` — BMS subcommands, parameters and examples
- `references/ims/guide.md` — IMS subcommands, parameters and examples
- `references/as/guide.md` — AS subcommands, parameters and examples
- `references/cce/guide.md` — CCE subcommands, parameters and examples
- `references/iam-policies.md` — required IAM read-only permissions
- `references/verification-method.md` — static, credential and live verification checklist
- `references/acceptance-criteria.md` — skill test acceptance checklist
- `references/cli-installation-guide.md` — out-of-scope operations and KooCLI boundary
