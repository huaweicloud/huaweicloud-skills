---
name: huawei-cloud-sms-host-migrator
description: |
  End-to-end host migration assistant powered by Huawei Cloud Server Migration Service (SMS).
  Assists users in discovering on-premise IDC or third-party cloud hosts (Alibaba Cloud ECS, Tencent Cloud CVM, AWS EC2), deploying SMS Agent, executing pre-migration compatibility checks, configuring target VM templates, orchestrating full and incremental replication, and performing smooth cutover to Huawei Cloud ECS or Flexus X.
  Triggers include: "主机迁移", "整机迁移", "创建SMS迁移任务", "主机在线增量迁移与割接", "host migration", "server migration", "SMS agent deployment", "create SMS migration task", "incremental host migration and cutover", "migrate IDC to Huawei Cloud", "migrate cloud server to ECS".
tags: [huawei-cloud, sms, migration, host-migration, ecs]
---

# Huawei Cloud SMS Host Migrator

The **Huawei Cloud SMS Host Migrator** skill automates and guides the full lifecycle of host migration from on-premise IDCs or third-party clouds (Alibaba Cloud, Tencent Cloud, AWS) to Huawei Cloud ECS or Flexus X instances using the Huawei Cloud Server Migration Service (SMS).

## Overview

The migration process supports file-level replication (`MIGRATE_FILE`) for Linux source hosts and block-level replication (`MIGRATE_BLOCK`) for Windows Server source hosts.

Key capabilities provided:
- **Guided Agent Deployment**: Generate installation instructions for Linux and Windows Server source machines.
- **Pre-migration Compatibility Diagnostics**: Automatic checks for OS version, firmware (BIOS/UEFI), disk partition table (MBR/GPT), file system, and required network ports.
- **Target Specification Modeling**: Provision migration templates targeting Huawei Cloud standard ECS or cost-effective Flexus X instances.
- **Replication Orchestration**: Track replication tasks, remaining time (`remain_seconds`), throttling limits, progress percentages, and subtask states.
- **Cutover and Validation**: Execute incremental sync windows, detach migration drivers, and verify target host boot status.

## Prerequisites

1. **KooCLI (`hcloud`)**: Installed and authenticated with a valid profile (`cn-north-4`, `ap-southeast-3`, etc.).
   - Follow instructions in `references/cli-installation-guide.md`.
2. **Target Security Group Inbound Rules**:
   The destination ECS security group **must** allow specific inbound ports strictly from the source server IP:
   - **Linux**: Inbound TCP port `22` (secure rsync over SSH).
   - **Windows Server**: Inbound TCP ports `22` (initialization), `8899` (control channel), and `8900` (block data streaming).
   - **Default Creation Behavior**: By default, create a dedicated new security group populated strictly with these rules rather than reusing an existing group.
   - **Target Outbound Rules**: Outbound TCP port `443` allowed to SMS API and Huawei Cloud services.
   - **Target Subnet Network ACL**: Ensure associated subnet ACLs allow matching inbound ports and return ephemeral ports.
   - *Security Guardrail*: Do **not** set source address to `0.0.0.0/0`; restrict strictly to source server IP.
3. **Source Server Network & Environment**:
   - Outbound TCP port `443` open to SMS control plane: `sms.cn-north-4.myhuaweicloud.com` (China Site) or `sms.ap-southeast-3.myhuaweicloud.com` (International Site - Singapore).
   - Outbound TCP ports `22`, `8899`, `8900` open to target ECS (public EIP or private IP via VPN/Direct Connect).
   - **NTP Time Synchronization**: Source system clock drift must be within **15 minutes** of standard time.
   - **Dependencies**: Linux requires `rsync`, `tar`, `nohup`, `python`; Windows requires PowerShell 3.0+ and VSS service.
   - **Disk Space**: Linux root partition (`/`) ≥ 200 MB free space; Windows partitions ≥ 600 MB require ≥ 320 MB free space.
4. **IAM Permissions**: Sufficient permissions for `SMS FullAccess`, `ECS CommonOperations`, `VPC Administrator`, and `EVS CommonOperations`.
   - See least-privilege definitions in `references/iam-policies.md`.
   - See complete pre-migration checklist in `references/pre-migration-checklist.md`.

## Workflow

1. **Phase 1 - Assessment & Scenario Selection**:
   - **Scenario A (Source Host Already Registered)**: Locate the host using `hcloud SMS ListServers --cli-region={region}`, retrieve `source_server_id`, verify 14 pre-checks via `ShowServer`, and proceed to Phase 3 (skip Phase 2).
   - **Scenario B (Fresh Host / Agent Not Installed)**: Perform preliminary prerequisites (OS support, NTP drift ≤ 15 min, network connectivity) and proceed to Phase 2 for agent deployment (verify registration via `ListServers` post-installation).
   *(Note: If registration state is unknown, run `hcloud SMS ListServers --cli-region={region}` first).*
2. **Phase 2 - Agent Deployment & Registration (Scenario B Only)**: Deploy OS-specific agent and authenticate out-of-band with AK/SK, SMS domain (`sms.cn-north-4.myhuaweicloud.com` for China Site; `sms.ap-southeast-3.myhuaweicloud.com` for International Site Singapore), and Enterprise Project ID.
3. **Phase 3 - Target Security Group & Destination Provisioning**:
   - Create a dedicated target security group with minimal inbound rules (Linux: port 22; Windows: ports 22, 8899, 8900) restricted to the source IP (public egress IP for internet; private IP for VPN/Direct Connect).
   - **Target Provisioning Branching (BIOS/Linux vs UEFI Windows)**:
     - **Standard Mode (BIOS Hosts & Linux)**: Create a target template (`CreateTemplate`) with VPC, subnet, flavor, image ID (from IMS), and network binding (300M pay-per-traffic EIP for public mode; `{}` for private mode).
     - **Existing Server Mode (Mandatory for UEFI Windows)**: SMS does not support auto-provisioning via templates for UEFI Windows. **Do not create a migration template**. Pre-create the target ECS on Huawei Cloud with UEFI boot mode (`hw_firmware_type: "uefi"`), matching disk layout, and proceed directly to Phase 4.
4. **Phase 4 - Replication Task Execution**: Create migration task (name: 4–20 chars) with disk layout mapped from `ShowServer`. For BIOS/Linux, link `vm_template_id` (`exist_server: false`); for UEFI Windows, specify `target_server.vm_id` (`exist_server: true`, `type: MIGRATE_BLOCK`). Route replication traffic via public EIP (`use_public_ip: true`) or private IP (`use_public_ip: false`). Monitor progress and adjust speed if needed.
5. **Phase 5 - Incremental Sync & Cutover**: Run delta synchronization passes during maintenance window, finalize cutover via `UpdateTaskStatus --operation="clear"`, verify source server transitions to `cleared` state (task remains `MIGRATE_SUCCESS`), and clean up resources in Task → Template sequence.

> [!IMPORTANT]
> Mutating operations (such as creating migration tasks, pausing/restarting tasks, modifying templates, and triggering cutover) alter cloud resources. Always confirm parameters with the user before executing mutating commands.

## Core Commands

### 1. Assessment & Server Discovery (Read-Only)

View current migration overview statistics across all lifecycle states:
```bash
hcloud SMS ShowOverview --cli-region=cn-north-4
```

#### Decision Branching:
- **Scenario A (Source Server Registered in SMS)**:
  Query registered servers to locate the target host and retrieve its ID:
  ```bash
  hcloud SMS ListServers --cli-region=cn-north-4 --limit=10
  ```
  Optionally filter by hostname:
  ```bash
  hcloud SMS ListServers --cli-region=cn-north-4 --name="source-host-01"
  ```
  Inspect detailed source server configuration, disk layout, and automated pre-check results:
  ```bash
  hcloud SMS ShowServer --cli-region=cn-north-4 --source_id={source_server_id}
  ```
  - When all 14 pre-checks report `result: "OK"`, **skip Phase 2 (Agent Deployment)** and jump directly to **Phase 3 (Target Template Management)**.
  - If `state: "unavailable"`, the agent is disconnected; guide the user to restart the agent on the source host (`sudo ./startup.sh` on Linux or restart `SMS-Agent` Windows service).

- **Scenario B (Fresh Host / Agent Not Installed)**:
  - The source host is not yet registered in SMS. Perform preliminary offline checks (see `references/pre-migration-checklist.md`).
  - Proceed directly to **Phase 2 (Agent Deployment & Registration)** (see `references/agent-deployment-guide.md`).
  - Once the agent runs and registers, query `hcloud SMS ListServers --cli-region=cn-north-4` to confirm registration and obtain `source_server_id`.

List existing migration projects:
```bash
hcloud SMS ListMigprojects --cli-region=cn-north-4
```

### 2. Target Security Group & Template Management

#### Step 2.1: Create Dedicated Target Security Group
By default, create a new dedicated security group rather than reusing an existing group:
```bash
hcloud VPC CreateSecurityGroup --cli-region=cn-north-4 --security_group.name=sg-sms-target-migration --security_group.description="Dedicated security group for SMS target ECS"
```

Add ingress rules restricted to source server IP:
> [!IMPORTANT]
> **Source IP Selection**:
> - **Public IP (Default)**: For internet migrations, set `remote_ip_prefix` to the source host's public egress IP (`{source_public_ip}/32`).
> - **Private IP**: Use source private IP (`{source_private_ip}/32`) only when private network connectivity (VPN/Direct Connect) is established.

- For Linux (Port 22):
```bash
hcloud VPC CreateSecurityGroupRule --cli-region=cn-north-4 --security_group_rule.security_group_id="{sg_id}" --security_group_rule.direction="ingress" --security_group_rule.protocol="tcp" --security_group_rule.multiport="22" --security_group_rule.remote_ip_prefix="{source_public_ip}/32"
```

- For Windows Server (Ports 22, 8899, 8900):
```bash
hcloud VPC CreateSecurityGroupRule --cli-region=cn-north-4 --security_group_rule.security_group_id="{sg_id}" --security_group_rule.direction="ingress" --security_group_rule.protocol="tcp" --security_group_rule.multiport="22,8899,8900" --security_group_rule.remote_ip_prefix="{source_public_ip}/32"
```

#### Step 2.2: Target Provisioning & Destination Setup

Before configuring the target, determine the provisioning path based on the source host firmware:
> [!IMPORTANT]
> - **BIOS-boot Hosts & Linux**: Auto-provisioning via a dedicated target template (`CreateTemplate`) is supported. Proceed with the template workflow below.
> - **UEFI Windows Hosts (Existing Server Mode Mandatory)**: SMS **does NOT support auto-provisioning via migration templates for UEFI Windows hosts**. You **must NOT create a migration template**.
>   1. Pre-create a new target ECS on Huawei Cloud first (ensure UEFI boot mode `hw_firmware_type: "uefi"`, matching vCPU/RAM, and disk size >= source disk).
>   2. Skip `CreateTemplate`.
>   3. Proceed directly to **Phase 4** and create the task using `templates/create-task-existing-server.json` with `"exist_server": true` and `"target_server.vm_id": "{target_ecs_vm_id}"`.

Query target VPC and Subnet configurations:
```bash
# Query VPC with pinned API version v3 to avoid multi-version preamble text breaking JSON parsing:
hcloud VPC ListVpcs/v3 --cli-region=cn-north-4 --limit=10

# Query subnets in the target VPC:
hcloud VPC ListSubnets --cli-region=cn-north-4 --vpc_id="{vpc_id}" --limit=10
```

Query target Project ID for the region:
```bash
# Query project ID for the specified target region (e.g., cn-north-4):
hcloud IAM KeystoneListProjects --cli-region=cn-north-4 --name="cn-north-4" --cli-query="projects[0].id"

# Or list all projects authorized for the account:
hcloud IAM KeystoneListAuthProjects
```

Query Image Management Service (IMS) to obtain the target OS `image_id`:
> [!NOTE]
>
> - **Linux Images**: Query public/gold images using `--__imagetype="gold"` with `--__platform`.
> - **Windows Server Images**: Windows images on Huawei Cloud are provided under **Marketplace Images**. Query using `--__imagetype="market"` with `--__platform="Windows"`.

```bash
# Query active public Linux images by platform (e.g., Ubuntu, CentOS, Debian, EulerOS):
hcloud IMS ListImages --cli-region=cn-north-4 --status=active --__imagetype="gold" --__platform="Ubuntu" --limit=10

# Query active Windows Server images under Marketplace Images (__imagetype="market") using platform filtering:
hcloud IMS ListImages --cli-region=cn-north-4 --status=active --__imagetype="market" --__platform="Windows" --limit=10
```
Extract the image UUID (`id`) and populate the `"image_id"` field in `templates/create-template.json` (or use it when pre-creating the target ECS).

Create a target template using a JSON specification file:
> [!IMPORTANT]
> - **JSON Encapsulation**: KooCLI requires the template definition inside a top-level `"body"` object to pass all REST API fields directly.
> - **Public vs. Private Network (`publicip`)**:
>   - **Public Internet (Default)**: Target ECS requires an EIP. Configure pay-per-traffic 300M bandwidth:
>     `"publicip": { "type": "5_bgp", "bandwidth_size": 300, "bandwidth_share_type": "PER" }`
>   - **Private Intranet (VPN/Direct Connect)**: Omit public IP by configuring `"publicip": {}`.

```bash
hcloud SMS CreateTemplate --cli-region=cn-north-4 --cli-jsonInput="templates/create-template.json"
```

Customize target ECS parameters (flavor, VPC, subnet, security group, disk size, and bandwidth) in [templates/create-template.json](templates/create-template.json).

### 3. Migration Task Orchestration

List ongoing or past migration tasks:
```bash
hcloud SMS ListTasks --cli-region=cn-north-4 --limit=10
```

Inspect migration task status, progress percentage, subtasks, and remaining time (`remain_seconds`, `estimate_complete_time`):
```bash
# Query full task details:
hcloud SMS ShowTask --cli-region=cn-north-4 --task_id={task_id}

# Or extract remaining time and replication speed directly:
hcloud SMS ShowTask --cli-region=cn-north-4 --task_id={task_id} --cli-query="{RemainingSeconds:remain_seconds,SpeedMBs:migrate_speed,EstimateComplete:estimate_complete_time}"
```

Create a migration task using a JSON specification file:
> [!IMPORTANT]
> - **JSON Encapsulation**: KooCLI requires task parameters wrapped inside a top-level `"body"` object to pass all fields directly.
> - **Task Name Length**: Length must be between 4 and 20 characters (`4 <= length <= 20`). Avoid overly long names.
> - **Replication Type (`type`)**: Use `"MIGRATE_FILE"` for Linux and `"MIGRATE_BLOCK"` for Windows.
> - **Target Mode (`exist_server` vs `vm_template_id`)**:
>   - **Template mode (BIOS/Linux)**: Set `"exist_server": false`, `"vm_template_id": "{template_id}"`, and `"vm_id": ""`.
>   - **Existing server mode (UEFI Windows)**: Set `"exist_server": true`, `"target_server.vm_id": "{target_ecs_vm_id}"`, and `"vm_template_id": ""`.
> - **Target Disks Sourcing**: Map `disks` directly from `hcloud SMS ShowServer --cli-region={region} --source_id={source_server_id}`.
> - **Windows Disk Path Double-Escaping (KooCLI Workaround)**:
>   Due to a KooCLI JSON serialization defect (tested on v7.2.12), backslashes in Windows partition paths and UUIDs must be double-escaped in `--cli-jsonInput` files (use 4 backslashes, e.g., `"name": "C:\\\\"`). Use `templates/create-task-windows.json` (BIOS) or `templates/create-task-existing-server.json` (UEFI). *Note: If a future KooCLI update fixes this serialization defect, revert to standard JSON escaping (`"name": "C:\\"`). Verify outbound payload using `--dryrun` when updating KooCLI.* See `references/troubleshooting-guide.md`.

```bash
# Create task for Linux source host (template auto-provisioning):
hcloud SMS CreateTask --cli-region=cn-north-4 --cli-jsonInput="templates/create-task.json"

# Create task for BIOS Windows source host (template auto-provisioning):
hcloud SMS CreateTask --cli-region=cn-north-4 --cli-jsonInput="templates/create-task-windows.json"

# Create task for UEFI Windows host (pre-created existing server mode):
hcloud SMS CreateTask --cli-region=cn-north-4 --cli-jsonInput="templates/create-task-existing-server.json"
```

For complete task definitions across operating systems and provisioning modes, see the pre-configured templates:
- **Linux (Template Auto-Provisioning)**: [templates/create-task.json](templates/create-task.json)
- **Windows BIOS (Template Auto-Provisioning)**: [templates/create-task-windows.json](templates/create-task-windows.json)
- **Windows UEFI (Existing Server Mode)**: [templates/create-task-existing-server.json](templates/create-task-existing-server.json)

Control migration task state (`start`, `stop`, `clear`, `restart`):
> [!NOTE]
> After executing `clear`, the migration task status remains `MIGRATE_SUCCESS`, while the source server status (`ShowServer` -> `state`) transitions to `"cleared"`.

```bash
# Start or pause replication task:
hcloud SMS UpdateTaskStatus --cli-region=cn-north-4 --task_id={task_id} --operation="start"

# Finalize cutover and clean up replication snapshots:
hcloud SMS UpdateTaskStatus --cli-region=cn-north-4 --task_id={task_id} --operation="clear"

# Confirm cutover completion on source server:
hcloud SMS ShowServer --cli-region=cn-north-4 --source_id={source_server_id}
```

Adjust replication speed throttling limit (0-1000 Mbit/s):
```bash
hcloud SMS UpdateSpeed --cli-region=cn-north-4 --task_id={task_id} --speed_limit.1.start="00:00" --speed_limit.1.end="24:00" --speed_limit.1.speed=50
```

### 4. Resource Cleanup Sequence (Task → Template)

Clean up migration resources in strict sequence after cutover or task completion:
> [!IMPORTANT]
> - **Strict Deletion Order (Task → Template)**: A target template cannot be deleted while linked to an active task (returns `SMS.7111`). Always delete the task first.
> - **Automatic Template Removal (`SMS.7101`)**: When a task is created with auto-provisioning (`exist_server: false`), deleting the task may automatically delete the associated template. If `DeleteTemplate` subsequently returns `SMS.7101` (Template not found), it has already been cleaned up and can be safely ignored.

1. Delete migration task first:
```bash
hcloud SMS DeleteTask --cli-region=cn-north-4 --task_id={task_id}
```

2. Delete target template:
```bash
hcloud SMS DeleteTemplate --cli-region=cn-north-4 --id={template_id}
```

### 5. Network Diagnostics & Troubleshooting

Inspect target security group rules and subnet network ACLs:
```bash
# Query inbound rules on the destination security group:
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --security_group_id.1="{sg_id}"

# Query subnet firewall / network ACL policies:
hcloud VPC ListFirewall --cli-region=cn-north-4
```

Inspect target ECS status and release target resources:
```bash
# Query target ECS status and attributes:
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id="{target_ecs_vm_id}"

# Remove stalled or failed migration task to release target resources:
hcloud SMS DeleteTask --cli-region=cn-north-4 --task_id={task_id}
```

## Parameter Confirmation

Before creating templates or executing migration tasks, confirm the following parameters:

| Parameter | Required | Description | Example Value |
|---|---|---|---|
| `--cli-region` | Yes | Target Huawei Cloud region: `cn-north-4` (China Site) or `ap-southeast-3` (International Site - Singapore) | `cn-north-4` / `ap-southeast-3` |
| `source_server_id` | Yes | Source server UUID registered with SMS (retrieved from `ListServers` in Scenario A, or post-registration in Scenario B) | `d8c8c498-2e90-499e-a022-4c0463ab1c98` |
| `os_type` | Yes | Operating system family (`LINUX` or `WINDOWS`) | `LINUX` / `WINDOWS` |
| `migration_type` | Yes | Replication data copy type (`MIGRATE_FILE` for Linux; `MIGRATE_BLOCK` for Windows) | `MIGRATE_FILE` (Linux) / `MIGRATE_BLOCK` (Windows) |
| `flavor` | Yes | Target Huawei Cloud ECS instance specification | `c7.large.2` / `x1.2u.4g` (Flexus X) |
| `image_id` | Conditional | Target OS image UUID queried via IMS using `--__platform` (Linux: `--__imagetype="gold" --__platform=...`; Windows: `--__imagetype="market" --__platform="Windows"`; used for template or pre-creating target ECS) | `c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f` |
| `firmware` | Yes | Source host boot firmware from `ShowServer` (`BIOS` or `UEFI`). UEFI Windows requires existing server mode. | `BIOS` / `UEFI` |
| `exist_server` | Yes | Target server mode: `false` for template auto-provisioning (BIOS/Linux); `true` for pre-created existing server (mandatory for UEFI Windows) | `false` / `true` |
| `vm_id` | Conditional | Target ECS UUID (required when `exist_server=true`, e.g., UEFI Windows; empty string for template auto-provisioning) | `e7b8c9d0-1a2b-3c4d-5e6f-7a8b9c0d1e2f` |
| `vm_template_id` | Conditional | Target template UUID from `CreateTemplate` (used when `exist_server=false`; empty string when `exist_server=true`) | `e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b` |
| `vpc_id` | Yes | Target Virtual Private Cloud UUID | `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d` |
| `subnet_id` | Yes | Target VPC Subnet UUID | `b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e` |
| `sg_id` | Yes | Target Security Group UUID (by default, created newly with minimal rules; or specify existing SG) | `c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f` |
| `source_ip` | Yes | Source server IP for target SG ingress: public egress IP (`{source_public_ip}`) for internet; private IP (`{source_private_ip}`) for VPN/Direct Connect | `198.51.100.25` (Public) / `10.0.1.50` (Private) |
| `project_id` | Yes | Target Huawei Cloud Project UUID queried via `hcloud IAM KeystoneListProjects --name="{region}" --cli-query="projects[0].id"` | `a64c6153e3c646e681cc664726d8a24d` |
| `project_name` | Yes | Target Huawei Cloud Project Name | `cn-north-4` |
| `target_server_name` | Yes | Target ECS instance name | `ecs-target-server-01` |
| `task_name` | Yes | Migration task name (4–20 characters; avoid overly long names) | `MigrationTask` |
| `target_disks` | Yes | Target disk and partition mapping retrieved from `hcloud SMS ShowServer --cli-region={region} --source_id={source_server_id}` | Sourced from `ShowServer` output |
| `network_mode` | Yes | Network replication mode (`PUBLIC` internet by default; `PRIVATE` for VPN / Direct Connect / VPC Peering) | `PUBLIC` / `PRIVATE` |
| `publicip` | Yes | Template EIP: pay-per-traffic 300M (`bandwidth_size: 300`) in PUBLIC mode; `{}` in PRIVATE mode | Configured per `network_mode` |
| `use_public_ip` | Yes | Task public IP flag (`true` in PUBLIC mode; `false` in PRIVATE mode) | `true` (PUBLIC) / `false` (PRIVATE) |
| `migration_ip` | No | Task migration IP (`""` in PUBLIC mode; target private IP in PRIVATE mode) | `""` (PUBLIC) / `172.16.10.100` (PRIVATE) |
| `speed_limit` | No | Bandwidth throttle limit in MB/s (0 = unlimited) | `50` |
| `start_target_server`| No | Auto-start target ECS upon replication finish (`true`/`false`) | `false` |

## KooCLI Command Format Standard

All KooCLI commands must adhere to the standard syntax:
```bash
hcloud <Service> <Operation> --cli-region=<region> [--param1=value1 ...]
```

- **Service**: Exact KooCLI service identifier starting with uppercase/title case (e.g., `SMS`, `ECS`, `VPC`).
- **Operation**: PascalCase operation identifier (e.g., `ListServers`, `ShowOverview`, `CreateTask`).
- **Region**: Mandatory parameter `--cli-region=<region_id>` specifying the target cloud region.
- **Parameters**: Structured parameters use dot notation (e.g., `--vpc.id=xxx`, `--nics.1.id=yyy`).

## Reference Documents

- [cli-installation-guide.md](references/cli-installation-guide.md) — KooCLI installation and profile configuration
- [iam-policies.md](references/iam-policies.md) — Least-privilege IAM policies for SMS, ECS, VPC, and EVS
- [dataflow-diagram.md](references/dataflow-diagram.md) — Architecture and data flow diagrams for control and data planes
- [agent-deployment-guide.md](references/agent-deployment-guide.md) — Detailed agent installation procedures for Linux & Windows
- [pre-migration-checklist.md](references/pre-migration-checklist.md) — Compatibility checklist for OS, disk, and network ports
- [troubleshooting-guide.md](references/troubleshooting-guide.md) — Diagnostic commands, common SMS error codes, and recovery steps
- [related-commands.md](references/related-commands.md) — Command reference table for SMS CLI operations
