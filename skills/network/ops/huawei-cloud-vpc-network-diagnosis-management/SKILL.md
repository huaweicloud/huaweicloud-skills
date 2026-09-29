---
name: huawei-cloud-vpc-network-diagnosis-management
description: |
  Use when managing Huawei Cloud VPC (Virtual Private Cloud) networks — VPC/subnet CRUD operations,
  network connectivity diagnosis, port connectivity diagnosis, and subnet CIDR conflict analysis.
  Covers listing VPCs/subnets/route tables, querying VPC/subnet details, creating/updating/deleting
  VPCs and subnets, and diagnosing why networks or business ports are unreachable (route table gaps,
  subnet CIDR overlaps, security group rule blocking, port status).
  Provides 14 huawei_* actions: huawei_list_vpcs, huawei_list_subnets, huawei_get_vpc,
  huawei_get_subnet, huawei_list_route_tables, huawei_diagnose_network_connectivity,
  huawei_diagnose_port_connectivity, huawei_analyze_subnet_cidr_conflict, huawei_create_vpc,
  huawei_create_subnet, huawei_update_vpc, huawei_update_subnet, huawei_delete_vpc,
  huawei_delete_subnet.
  Service keywords: vpc, subnet, route table, router, network, CIDR, security group, port,
  elastic network interface, VPC, 子网, 路由表, 网络, 网段, 连通性, 端口, 安全组.
  Triggers include: "网络不通", "业务端口不通", "端口不通", "VPC 创建", "创建子网", "删除 VPC",
  "删除子网", "子网网段冲突", "CIDR 冲突", "路由表", "连通性诊断", "create vpc", "create subnet",
  "delete vpc", "delete subnet", "subnet conflict", "port connectivity", "network diagnosis".
tags: [huawei-cloud, vpc, network, diagnose, management]
---

# Huawei Cloud VPC Network Diagnosis & Configuration Management

**STOP - Do not answer from general knowledge. Follow the procedure below.**

Always run `hcloud VPC <Operation> --help` before constructing commands to discover exact
parameter names and requirements.

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

## Overview

This skill provides AI Agent capabilities for Huawei Cloud VPC (Virtual Private Cloud / 虚拟私有云):
VPC and subnet lifecycle management, route table inspection, and network/port connectivity diagnosis
to quickly locate the root cause of unreachable networks or business ports.

It enables four capability groups through 14 `huawei_*` actions:

| Capability | Risk level | Actions |
| ---------- | ---------- | ------- |
| Query (read-only) | R3 — auto execute | `huawei_list_vpcs`, `huawei_list_subnets`, `huawei_get_vpc`, `huawei_get_subnet`, `huawei_list_route_tables` |
| Diagnose (read-only) | R3 — auto execute | `huawei_diagnose_network_connectivity`, `huawei_diagnose_port_connectivity`, `huawei_analyze_subnet_cidr_conflict` |
| Manage | R2 — preview + confirm | `huawei_create_vpc`, `huawei_create_subnet`, `huawei_update_vpc`, `huawei_update_subnet` |
| Manage | R1 — preview + confirm | `huawei_delete_vpc`, `huawei_delete_subnet` |

**Scope boundaries:**

- ✅ List/query VPCs, subnets, route tables, ports, security groups
- ✅ Diagnose network connectivity (route table gaps, subnet CIDR conflicts, gateway reachability)
- ✅ Diagnose port connectivity (port status, admin state, security group rules, device binding)
- ✅ Create/update/delete VPCs and subnets (R2/R1: always preview + confirm first)
- ❌ NEVER manage security group rules themselves (security group rule CRUD is out of scope; use a dedicated security-group skill for that)
- ❌ NEVER create/delete route tables or ports — diagnosis reads them only
- ❌ NEVER echo credentials (AK/SK, passwords, tokens) in any output or report

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by
`scripts/ensure_cli.sh` if absent).

## Critical Warnings

| Trap | Why |
| ---- | --- |
| Deleting a VPC/subnet is irreversible | R1 actions: verify no associated resources (subnets in VPC, instances/ports in subnet) BEFORE deletion, then require explicit user confirmation |
| CIDR conflicts break connectivity | Overlapping subnet CIDRs inside a VPC, or a subnet CIDR not contained in the VPC CIDR, silently breaks routing — always run conflict analysis before creating subnets |
| Missing default route => no Internet | A route table without a `0.0.0.0/0` default route (or with a wrong nexthop) is the #1 cause of "network unreachable" |
| Port DOWN / admin_state_up=false | A port in `DOWN` state or with `admin_state_up=false` cannot carry traffic regardless of security groups |
| Security group rules are stateful | Inbound rules must exist for business ports; default `deny all` inbound blocks everything not explicitly allowed |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - Installation and configuration guide: see `references/cli-installation-guide.md`
   - Two supported authentication modes:
     - **AK/SK credentials**: environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
       (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`), or interactive setup via the hcloud configure wizard
     - **Local hcloud profile**: run "hcloud configure list"; it must show a valid profile with mode `AKSK`
       and a real `accessKeyId`
   - Verify authentication with "hcloud configure list"
2. **Region**: VPC is region-specific. Always pass `--cli-region={region}` (e.g. `cn-north-4`).
   `--project_id` is auto-filled from the profile when omitted.
3. **IAM permissions**: least-privilege policies are provided in `references/iam-policies.md`.
   - Query/diagnose: `vpc:listVpcs`, `vpc:showVpc`, `vpc:listSubnets`, `vpc:showSubnet`,
     `vpc:listRouteTables`, `vpc:showRouteTable`, `vpc:listPorts`, `vpc:showPort`,
     `vpc:listSecurityGroups`, `vpc:showSecurityGroup`
   - Manage: `vpc:createVpc`, `vpc:createSubnet`, `vpc:updateVpc`, `vpc:updateSubnet`,
     `vpc:deleteVpc`, `vpc:deleteSubnet`
4. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify target → region, vpc_id / subnet_id / port_id / instance_id, intent keywords
2. Classify intent →
     - Query/Diagnose (R3): list / show / analyze — auto execute
     - Manage (R2): create / update — ALWAYS show preview and ask for explicit confirmation
     - Manage (R1): delete — ALWAYS verify no associated resources, show preview, explicit confirmation
3. Execute → build the hcloud command from the verified templates below
4. Output → structured JSON summary + readable diagnosis report
5. Report quality → automatic via skill-quality-cli run wrapping (see Step 0 / Prerequisites #4)
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_vpc`, `huawei_create_subnet`, `huawei_update_vpc`,
  `huawei_update_subnet`): show the full command, the resource to be created/updated, and ask
  "confirm?" before running.
- **R1 actions** (`huawei_delete_vpc`, `huawei_delete_subnet`): first run the read-only checks
  (list subnets for a VPC; list ports/instances for a subnet). If associated resources exist,
  STOP and report them — do not delete. If clean, show the full command, the irreversible
  deletion warning, and require explicit confirmation.

Write operations are marked `[W]` / 写操作 in the command blocks below (检测关键字:
create / update / delete — same verbs the test pipeline's write-operation detector keys on).

## Core Commands

> All commands below are shown in **dual form**: the bare executable `hcloud VPC <Operation>`
> command and the identical payload wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- ...` for quality reporting.
> They require the **KooCLI (hcloud CLI)** installed and authenticated (see Prerequisites) — no
> Python SDK package is needed for any business command.

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- <command>` — bare
> `hcloud` calls are strictly forbidden.**

### 1. Query (R3 — read-only, auto execute)

**`huawei_list_vpcs`** — list all VPCs:

```bash
# Optional: --limit={n} --marker={marker} --name.1={name} --cidr.1={cidr} --enterprise_project_id={eps_id}
hcloud VPC ListVpcs --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ListVpcs --cli-region={region}
```

**`huawei_list_subnets`** — list all subnets (optionally scoped to one VPC):

```bash
# Optional: --vpc_id={vpc_id} --limit={n} --marker={marker}
hcloud VPC ListSubnets --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ListSubnets --cli-region={region}
```

**`huawei_get_vpc`** — query VPC details:

```bash
hcloud VPC ShowVpc --cli-region={region} --vpc_id={vpc_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ShowVpc --cli-region={region} --vpc_id={vpc_id}
```

**`huawei_get_subnet`** — query subnet details:

```bash
hcloud VPC ShowSubnet --cli-region={region} --subnet_id={subnet_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ShowSubnet --cli-region={region} --subnet_id={subnet_id}
```

**`huawei_list_route_tables`** — list route tables (optionally filtered by VPC/subnet):

```bash
# Optional: --vpc_id={vpc_id} --subnet_id={subnet_id} --id={routetable_id} --limit={n}
hcloud VPC ListRouteTables --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ListRouteTables --cli-region={region}
```

### 2. Diagnose (R3 — read-only, auto execute)

**`huawei_diagnose_network_connectivity`** — full VPC/subnet network connectivity diagnosis:

```bash
# Step 1: list all VPCs — 复用 §1: hcloud VPC ListVpcs --cli-region={region}
# Step 2: list all subnets — 复用 §1: hcloud VPC ListSubnets --cli-region={region}
# Step 3: list route tables — 复用 §1: hcloud VPC ListRouteTables --cli-region={region}
# Step 4: for each route table, show details:
# Optional: --project_id={project_id}
hcloud VPC ShowRouteTable --cli-region={region} --routetable_id={routetable_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ShowRouteTable --cli-region={region} --routetable_id={routetable_id}
```

Checks performed and reported:

| # | Check | Pass condition | Typical failure |
|---|-------|----------------|-----------------|
| 1 | Subnet CIDR inside VPC CIDR | Every subnet CIDR is contained in its VPC CIDR | Subnet created outside VPC range → unreachable |
| 2 | Subnet CIDR overlap | No two subnets in the same VPC overlap | Overlapping CIDRs → ambiguous routing |
| 3 | Default route exists | Each VPC route table has `0.0.0.0/0` or an equivalent catch-all | No default route → no Internet access |
| 4 | Route table association | Each subnet is associated with exactly one route table (or the default) | Orphan subnets use the default table unexpectedly |
| 5 | Gateway IP validity | Subnet `gateway_ip` is inside the subnet CIDR | Wrong gateway → hosts cannot reach gateway |

**`huawei_diagnose_port_connectivity`** — port-level connectivity diagnosis:

```bash
# Step 1: find ports of the target instance — Optional: --device_id={instance_id} --limit={n}
hcloud VPC ListPorts --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ListPorts --cli-region={region}
# Step 2: show port detail — check status, admin_state_up, device_owner, security_groups
hcloud VPC ShowPort --cli-region={region} --port_id={port_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ShowPort --cli-region={region} --port_id={port_id}
# Step 3: check the security groups bound to the port (verify inbound rules for the business port)
hcloud VPC ShowSecurityGroup --cli-region={region} --security_group_id={security_group_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC ShowSecurityGroup --cli-region={region} --security_group_id={security_group_id}
```

Checks performed and reported:

| # | Check | Pass condition | Typical failure |
|---|-------|----------------|-----------------|
| 1 | Port exists | `port_id` resolves | Port deleted / wrong region or project |
| 2 | Port status | `status == ACTIVE` | `DOWN` → device off, binding broken, or VM stopped |
| 3 | Admin state | `admin_state_up == true` | `false` → port administratively disabled |
| 4 | Device owner | Port bound to the expected device (`compute:` / `network:router_interface` etc.) | Unbound port belongs to no workload |
| 5 | Security group rules | An inbound rule allows the target protocol/port from the source CIDR | Default deny inbound → business port blocked |

**`huawei_analyze_subnet_cidr_conflict`** — subnet CIDR conflict detection:

```bash
# Step 1: list all VPCs — 复用 §1: hcloud VPC ListVpcs --cli-region={region}
# Step 2: list all subnets (per VPC) — 复用 §1: hcloud VPC ListSubnets --cli-region={region} --vpc_id={vpc_id}
# Analysis is computed locally on the returned CIDR strings (ipaddress module): overlap / containment / adjacency
```

Reports every conflict pair: identical CIDR, overlapping CIDRs, one containing another, and
subnets whose CIDR escapes their VPC CIDR.

### 3. Manage (R2 — preview + confirm)

**`huawei_create_vpc`** — create a VPC:

```bash
# [W] 写操作 (WRITE): creates a VPC — R2: preview + explicit confirmation required
# Optional: --vpc.description={description} --vpc.enterprise_project_id={eps_id} --vpc.tags.1={key*value}
hcloud VPC CreateVpc --cli-region={region} --vpc.name={name} --vpc.cidr={cidr}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC CreateVpc --cli-region={region} --vpc.name={name} --vpc.cidr={cidr}
```

**`huawei_create_subnet`** — create a subnet (must be inside the VPC CIDR, mask ≤ 28):

```bash
# [W] 写操作 (WRITE): creates a subnet — R2: preview + explicit confirmation required
# Optional: --subnet.description={description} --subnet.dhcp_enable=true --subnet.dnsList.1={dns_ip} --subnet.availability_zone={az}
hcloud VPC CreateSubnet --cli-region={region} --subnet.vpc_id={vpc_id} --subnet.name={name} --subnet.cidr={cidr} --subnet.gateway_ip={gateway_ip}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC CreateSubnet --cli-region={region} --subnet.vpc_id={vpc_id} --subnet.name={name} --subnet.cidr={cidr} --subnet.gateway_ip={gateway_ip}
```

**`huawei_update_vpc`** — update a VPC (name/description; CIDR can only be extended, never shrunk):

```bash
# [W] 写操作 (WRITE): modifies a VPC — R2: preview + explicit confirmation required
# Optional: --vpc.description={description} --vpc.cidr={new_cidr}（仅可扩大）
hcloud VPC UpdateVpc --cli-region={region} --vpc_id={vpc_id} --vpc.name={name}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC UpdateVpc --cli-region={region} --vpc_id={vpc_id} --vpc.name={name}
```

**`huawei_update_subnet`** — update a subnet (name/description/DNS/DHCP):

```bash
# [W] 写操作 (WRITE): modifies a subnet — R2: preview + explicit confirmation required
# Optional: --subnet.description={description} --subnet.dhcp_enable=true --subnet.dnsList.1={dns_ip}
hcloud VPC UpdateSubnet --cli-region={region} --vpc_id={vpc_id} --subnet_id={subnet_id} --subnet.name={name}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC UpdateSubnet --cli-region={region} --vpc_id={vpc_id} --subnet_id={subnet_id} --subnet.name={name}
```

### 4. Manage (R1 — preview + confirm)

**`huawei_delete_vpc`** — delete a VPC. **Only after confirming no subnets/associated resources remain:**

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes a VPC — R1: confirm empty, then explicit confirmation
# Pre-check: hcloud VPC ListSubnets --cli-region={region} --vpc_id={vpc_id}  (must return empty)
hcloud VPC DeleteVpc --cli-region={region} --vpc_id={vpc_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC DeleteVpc --cli-region={region} --vpc_id={vpc_id}
```

**WARNING (must be shown before execution):** deleting a VPC permanently removes the VPC and all
its remaining subnets, route tables, and default security group. If any subnets or associated
resources exist, STOP and report them — the API will refuse deletion with associated resources,
but you must verify first and NEVER force-delete.

**`huawei_delete_subnet`** — delete a subnet. **Only after confirming no instances/ports remain:**

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes a subnet — R1: confirm no instances/ports, then explicit confirmation
# Pre-check: hcloud VPC ListPorts --cli-region={region} --subnet_id={subnet_id}  (must return empty)
hcloud VPC DeleteSubnet --cli-region={region} --vpc_id={vpc_id} --subnet_id={subnet_id}
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC DeleteSubnet --cli-region={region} --vpc_id={vpc_id} --subnet_id={subnet_id}
```

**WARNING (must be shown before execution):** deleting a subnet permanently removes it. If any
ECS/ports remain in the subnet, the API will refuse; verify first and NEVER delete a subnet that
still has running instances.

## KooCLI Command Format Standard

```bash
hcloud VPC <Operation> --cli-region=<region> [--key=value ...]
skill-quality-cli run --skill-name huawei-cloud-vpc-network-diagnosis-management -- hcloud VPC <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | `VPC` (as shown by `hcloud VPC --help`; metadata dir is lowercase `vpc`) | `hcloud VPC ListVpcs --cli-region=cn-north-4` |
| Operation name | PascalCase (bare names default to the latest API version; append `/vN` to pin a version) | `ListVpcs`, `ShowVpc`, `ListSubnets`, `CreateSubnet`, `DeleteVpc` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--vpc_id=xxx` |
| Body parameter (nested) | `--vpc.name=value`, `--subnet.cidr=value` | `--subnet.gateway_ip=192.168.1.1` |
| Indexed parameter | `--key.N=value` | `--vpc.tags.1=env*prod` |
| Indexed array of objects | `--key.N.field=value` | `--subnet.extra_dhcp_opts.1.opt_name=ntp` |

## Parameter Confirmation

All parameters below were verified against `hcloud VPC <Operation> --help` (KooCLI 7.2.12).

### Query operations

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ListVpcs | `--limit` | int | No | `--limit=50` |
| ListVpcs | `--marker` | string | No | `--marker={last_id}` |
| ListVpcs | `--name.[N]` | array<string> | No | `--name.1=my-vpc` |
| ListVpcs | `--cidr.[N]` | array<string> | No | `--cidr.1=192.168.0.0/16` |
| ListVpcs | `--id.[N]` | array<string> | No | `--id.1={vpc_id}` |
| ListVpcs | `--description.[N]` | array<string> | No | `--description.1=prod` |
| ListVpcs | `--enterprise_project_id` | string | No | `--enterprise_project_id=0` |
| ListSubnets | `--vpc_id` | string | No | `--vpc_id={vpc_id}` |
| ListSubnets | `--limit` | int | No | `--limit=50` |
| ListSubnets | `--marker` | string | No | `--marker={last_id}` |
| ShowVpc | `--vpc_id` | string | **Yes** | `--vpc_id={vpc_id}` |
| ShowSubnet | `--subnet_id` | string | **Yes** | `--subnet_id={subnet_id}` |
| ListRouteTables | `--id` | string | No | `--id={routetable_id}` |
| ListRouteTables | `--vpc_id` | string | No | `--vpc_id={vpc_id}` |
| ListRouteTables | `--subnet_id` | string | No | `--subnet_id={subnet_id}` |
| ListRouteTables | `--limit` / `--marker` | int/string | No | `--limit=50` |
| ShowRouteTable | `--routetable_id` | string | **Yes** | `--routetable_id={routetable_id}` |
| ListPorts | `--device_id.[N]` | array<string> | No | `--device_id.1={instance_id}` |
| ListPorts | `--subnet_id` | string | No | `--subnet_id={subnet_id}` |
| ListPorts | `--status` | string | No | `--status=ACTIVE` |
| ListPorts | `--admin_state_up` | bool | No | `--admin_state_up=true` |
| ListPorts | `--limit` / `--marker` | int/string | No | `--limit=50` |
| ShowPort | `--port_id` | string | **Yes** | `--port_id={port_id}` |
| ShowSecurityGroup | `--security_group_id` | string | **Yes** | `--security_group_id={sg_id}` |

### Manage operations (write)

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| CreateVpc | `--vpc.name` | string | **Yes** | `--vpc.name=prod-vpc` |
| CreateVpc | `--vpc.cidr` | string | **Yes** | `--vpc.cidr=192.168.0.0/16` |
| CreateVpc | `--vpc.description` | string | No | `--vpc.description=prod` |
| CreateVpc | `--vpc.enterprise_project_id` | string | No | `--vpc.enterprise_project_id=0` |
| CreateVpc | `--vpc.tags.[N]` | array<string> | No | `--vpc.tags.1=env*prod` |
| CreateSubnet | `--subnet.vpc_id` | string | **Yes** | `--subnet.vpc_id={vpc_id}` |
| CreateSubnet | `--subnet.name` | string | **Yes** | `--subnet.name=app-subnet` |
| CreateSubnet | `--subnet.cidr` | string | **Yes** | `--subnet.cidr=192.168.1.0/24` |
| CreateSubnet | `--subnet.gateway_ip` | string | **Yes** | `--subnet.gateway_ip=192.168.1.1` |
| CreateSubnet | `--subnet.description` | string | No | `--subnet.description=app tier` |
| CreateSubnet | `--subnet.dhcp_enable` | bool | No | `--subnet.dhcp_enable=true` |
| CreateSubnet | `--subnet.dnsList.[N]` | array<string> | No | `--subnet.dnsList.1=100.125.1.250` |
| CreateSubnet | `--subnet.availability_zone` | string | No | `--subnet.availability_zone=cn-north-4a` |
| UpdateVpc | `--vpc_id` | string | **Yes** | `--vpc_id={vpc_id}` |
| UpdateVpc | `--vpc.name` | string | No | `--vpc.name=new-name` |
| UpdateVpc | `--vpc.description` | string | No | `--vpc.description=new-desc` |
| UpdateVpc | `--vpc.cidr` | string | No | `--vpc.cidr=10.0.0.0/8` (extend only) |
| UpdateSubnet | `--vpc_id` | string | **Yes** | `--vpc_id={vpc_id}` |
| UpdateSubnet | `--subnet_id` | string | **Yes** | `--subnet_id={subnet_id}` |
| UpdateSubnet | `--subnet.name` | string | **Yes** | `--subnet.name=new-name` |
| UpdateSubnet | `--subnet.description` | string | No | `--subnet.description=new-desc` |
| UpdateSubnet | `--subnet.dhcp_enable` | bool | No | `--subnet.dhcp_enable=false` |
| UpdateSubnet | `--subnet.dnsList.[N]` | array<string> | No | `--subnet.dnsList.1=100.125.1.250` |
| DeleteVpc | `--vpc_id` | string | **Yes** | `--vpc_id={vpc_id}` |
| DeleteSubnet | `--vpc_id` | string | **Yes** | `--vpc_id={vpc_id}` |
| DeleteSubnet | `--subnet_id` | string | **Yes** | `--subnet_id={subnet_id}` |

Common to all operations: `--cli-region` (required), `--project_id` (required by API but auto-filled
from the authenticated profile when omitted).

## Troubleshooting

| Error | Root cause → Fix |
| ----- | ---------------- |
| `VPC.XXXX` resource not found | Wrong region/project → verify `--cli-region` and the resource ID (`ListVpcs` first) |
| `APIGW.0301 Unauthorized` | Stale/invalid AK/SK or profile → re-run the hcloud configure wizard with valid credentials |
| DeleteVpc refused | VPC still contains subnets/resources → list subnets with `--vpc_id`, delete them first |
| DeleteSubnet refused | Subnet still has ports/instances → `ListPorts --subnet_id={subnet_id}`, release instances first |
| CreateSubnet invalid CIDR | Subnet not contained in VPC CIDR or mask > 28 → pick a CIDR inside the VPC range |
| Overlapping subnets | Two subnets in the same VPC overlap → run `huawei_analyze_subnet_cidr_conflict` and re-plan |
| No Internet from an ECS | Missing default route / wrong nexthop → `huawei_diagnose_network_connectivity` route table check |
| Business port unreachable | Security group inbound rule missing → `huawei_diagnose_port_connectivity` SG check |

## Security Considerations

- MUST verify a VPC/subnet is empty before deletion (R1) and NEVER force-delete resources.
- MUST preview every write command and obtain explicit confirmation before R2/R1 execution.
- MUST NOT echo AK/SK, passwords, tokens, or other credentials in any output or report.
- MUST use least-privilege IAM policies (see `references/iam-policies.md`).
- SHOULD prefer read-only diagnosis over trial-and-error writes when troubleshooting.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for VPC/subnet query and management
- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK + profile authentication
- `references/verification-method.md` — Verification method and acceptance checks
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria for the 14 huawei_* actions
- VPC Docs: https://support.huaweicloud.com/vpc/
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc