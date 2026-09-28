# Verification Method — huawei-cloud-sms-host-migrator

This document defines the functional verification procedures for the `huawei-cloud-sms-host-migrator` skill, mapping directly to each phase of the migration workflow with concrete verification steps and success criteria.

---

## Workflow Phase Verification Matrix

| Phase | Phase Name | Verification Method / Command | Primary Success Criteria |
|---|---|---|---|
| **Phase 1** | Assessment & Scenario Selection | `hcloud SMS ShowOverview`<br>`hcloud SMS ListServers`<br>`hcloud SMS ShowServer` | Migration overview retrieved; source host located; 14 pre-checks report `result: "OK"`. |
| **Phase 2** | Agent Deployment & Registration | Out-of-band agent installation<br>`hcloud SMS ListServers` | Source host registered with valid `source_server_id`; state transitions to `waiting-migrate` or `waiting-test`. |
| **Phase 3** | Target Security Group & Destination Provisioning | `hcloud VPC CreateSecurityGroup`<br>`hcloud VPC CreateSecurityGroupRule`<br>`hcloud SMS CreateTemplate` | Dedicated SG created with minimal ports (22 for Linux; 22, 8899, 8900 for Windows); template or UEFI ECS provisioned. |
| **Phase 4** | Replication Task Execution | `hcloud SMS CreateTask`<br>`hcloud SMS ShowTask`<br>`hcloud SMS UpdateSpeed` | Task created; subtasks progress through stages to 100% replication without fatal disk or network errors. |
| **Phase 5** | Incremental Sync & Cutover | `hcloud SMS UpdateTaskStatus --operation="clear"`<br>`hcloud SMS ShowServer`<br>`hcloud SMS DeleteTask` | Source host transitions to `cleared`; target ECS status is `ACTIVE`; task cleaned up before template. |

---

## Phase 1: Assessment & Scenario Selection Verification

### Objective
Identify the migration scenario, evaluate source host readiness, and determine the provisioning path.

### Verification Steps
1. Query regional migration overview statistics:
   ```bash
   hcloud SMS ShowOverview --cli-region=cn-north-4
   ```
2. Query registered servers to identify the source host:
   ```bash
   hcloud SMS ListServers --cli-region=cn-north-4 --limit=10
   ```
3. Query detailed server diagnostics and pre-check status:
   ```bash
   hcloud SMS ShowServer --cli-region=cn-north-4 --source_id={source_server_id}
   ```

### Success Criteria
- **Overview Query**: Returns JSON object with status counters (`replicate`, `unconfigured`, `finished`, `cleared`).
- **Scenario Determination**:
  - **Scenario A (Host Pre-Registered)**: `ListServers` returns host matching target hostname or IP. Proceed to Step 3.
  - **Scenario B (Fresh Host)**: Host is absent from `ListServers`. Skip to Phase 2 for agent deployment.
- **Pre-Check Evaluation (Scenario A)**:
  - Host state is `waiting-migrate` or `waiting-test`.
  - All 14 automated pre-check items in `ShowServer` output report `"result": "OK"`.
  - Firmware (`firmware: "BIOS"` or `"firmware": "UEFI"`) and disk partition tables (`partition_style: "MBR"` or `"GPT"`) are cataloged.
- **Failure Indicator & Action**: If `state: "unavailable"`, source agent is stopped; restart agent service on the source host. If pre-checks fail, consult `references/pre-migration-checklist.md`.

---

## Phase 2: Agent Deployment & Registration Verification (Scenario B Only)

### Objective
Deploy the SMS Agent on a fresh source host, establish outbound HTTPS connectivity, and register the machine with the Huawei Cloud SMS control plane.

### Verification Steps
1. Inspect running agent process on the source machine:
   - **Linux**: `ps aux | grep -i sms-agent`
   - **Windows**: `Get-Service SMS-Agent`
2. Confirm host registration on Huawei Cloud:
   ```bash
   hcloud SMS ListServers --cli-region=cn-north-4 --name="{source_hostname}"
   ```
3. Query source server details:
   ```bash
   hcloud SMS ShowServer --cli-region=cn-north-4 --source_id={source_server_id}
   ```

### Success Criteria
- **Process Status**: Agent process or Windows service is in active running state.
- **Registration Confirmation**: `ListServers` returns a non-empty item array with the registered host.
- **Server Identity**: `source_server_id` is assigned and persistent.
- **Pre-Check Generation**: Automated diagnostics run and report `result: "OK"` across all 14 checks.
- **Failure Indicator & Action**: If registration times out, verify outbound TCP port `443` access to `sms.cn-north-4.myhuaweicloud.com` (China Site) or `sms.ap-southeast-3.myhuaweicloud.com` (International Site) and verify system clock drift is within 15 minutes.

---

## Phase 3: Target Security Group & Destination Provisioning Verification

### Objective
Provision a dedicated security group with least-privilege ingress restricted to the source server IP, and configure destination compute resources.

### Verification Steps
1. Create dedicated security group:
   ```bash
   hcloud VPC CreateSecurityGroup --cli-region=cn-north-4 --security_group.name="sg-sms-target-migration" --security_group.description="Dedicated security group for SMS target ECS"
   ```
2. Add ingress rules restricted to source server public or private IP:
   - **Linux (Port 22)**:
     ```bash
     hcloud VPC CreateSecurityGroupRule --cli-region=cn-north-4 --security_group_rule.security_group_id="{sg_id}" --security_group_rule.direction="ingress" --security_group_rule.protocol="tcp" --security_group_rule.multiport="22" --security_group_rule.remote_ip_prefix="{source_ip}/32"
     ```
   - **Windows Server (Ports 22, 8899, 8900)**:
     ```bash
     hcloud VPC CreateSecurityGroupRule --cli-region=cn-north-4 --security_group_rule.security_group_id="{sg_id}" --security_group_rule.direction="ingress" --security_group_rule.protocol="tcp" --security_group_rule.multiport="22,8899,8900" --security_group_rule.remote_ip_prefix="{source_ip}/32"
     ```
3. Destination provisioning check:
   - **Standard Mode (BIOS Hosts & Linux)**:
     ```bash
     hcloud SMS CreateTemplate --cli-region=cn-north-4 --cli-jsonInput="templates/create-template.json"
     ```
   - **Existing Server Mode (UEFI Windows Hosts)**:
     Ensure target ECS is pre-created with UEFI firmware:
     ```bash
     hcloud ECS ShowServer --cli-region=cn-north-4 --server_id="{target_ecs_vm_id}"
     ```

### Success Criteria
- **Security Group**: New security group created; rule creation returns valid `security_group_rule.id`. Remote IP prefix is restricted to `{source_ip}/32` (never `0.0.0.0/0`).
- **Template Mode (BIOS/Linux)**: `CreateTemplate` returns valid `template_id`; template includes correct VPC, subnet, target flavor, disk size, and 300M pay-per-traffic EIP configuration (for public mode).
- **Existing Server Mode (UEFI Windows)**: Pre-created target ECS exists with status `SHUTOFF` or `ACTIVE`, `hw_firmware_type: "uefi"`, and disk sizes greater than or equal to source disks. No SMS template is created.
- **Failure Indicator & Action**: If `CreateTemplate` fails with schema errors, confirm JSON payload is nested within the top-level `"body"` object.

---

## Phase 4: Replication Task Execution Verification

### Objective
Create and monitor the host replication task, validating subtask state transitions and data transfer progress.

### Verification Steps
1. Create replication task using mode-specific template:
   ```bash
   hcloud SMS CreateTask --cli-region=cn-north-4 --cli-jsonInput="templates/create-task.json"
   ```
2. Track replication progress and metrics:
   ```bash
   hcloud SMS ShowTask --cli-region=cn-north-4 --task_id={task_id}
   ```
3. Optionally adjust bandwidth throttle:
   ```bash
   hcloud SMS UpdateSpeed --cli-region=cn-north-4 --task_id={task_id} --speed_limit.1.start="00:00" --speed_limit.1.end="24:00" --speed_limit.1.speed=50
   ```

### Success Criteria
- **Task Creation**: `CreateTask` returns valid `task_id`; task name length is between 4 and 20 characters.
- **Subtask Progression**: Subtasks sequentially transition through operational states:
  1. `CREATE_CLOUD_SERVER`
  2. `SSL_CONFIG`
  3. `ATTACH_AGENT_IMAGE`
  4. `FORMAT_DISK`
  5. `MIGRATE_BLOCK` (Windows) / `MIGRATE_FILE` (Linux)
  6. `CONFIGURE_OS`
  7. `DETTACH_AGENT_IMAGE`
- **Replication Metrics**: Task `state` reaches `migrating` or `syncing`, `migrate_speed` is positive, and progress percentage advances to 100%.
- **Failure Indicator & Action**: If task creation fails with partition path errors on Windows, verify 4-backslash double-escaping in JSON (`"name": "C:\\\\"`). If replication stops, verify security group ports (22, 8899, 8900) via `hcloud VPC ListSecurityGroupRules/v3 --security_group_id.1="{sg_id}"` and subnet network ACLs via `hcloud VPC ListFirewall`.

---

## Phase 5: Incremental Sync & Cutover Verification

### Objective
Execute incremental delta replication during the maintenance window, perform final cutover, verify destination server boot, and clean up migration artifacts.

### Verification Steps
1. Trigger incremental sync / start replication:
   ```bash
   hcloud SMS UpdateTaskStatus --cli-region=cn-north-4 --task_id={task_id} --operation="start"
   ```
2. Execute cutover command:
   ```bash
   hcloud SMS UpdateTaskStatus --cli-region=cn-north-4 --task_id={task_id} --operation="clear"
   ```
3. Verify source and target states post-cutover:
   ```bash
   hcloud SMS ShowServer --cli-region=cn-north-4 --source_id={source_server_id}
   hcloud ECS ShowServer --cli-region=cn-north-4 --server_id="{target_ecs_vm_id}"
   ```
4. Clean up resources in strict Task → Template order:
   ```bash
   hcloud SMS DeleteTask --cli-region=cn-north-4 --task_id={task_id}
   hcloud SMS DeleteTemplate --cli-region=cn-north-4 --id={template_id}
   ```

### Success Criteria
- **Cutover Execution**: `UpdateTaskStatus` returns HTTP 200 with operation `"clear"` acknowledged.
- **State Transition**:
  - Source server `state` in `ShowServer` transitions to `"cleared"`.
  - Task state remains `"MIGRATE_SUCCESS"`.
- **Target Server Activation**: Target ECS starts up and attains status `"ACTIVE"`.
- **Service Verification**: Target ECS responds to SSH (Linux port 22) or RDP (Windows port 3389) connectivity tests; applications pass smoke testing.
- **Resource Deletion Order**: Task is deleted first via `DeleteTask`. Target template is deleted second via `DeleteTemplate` (safe to ignore `SMS.7101` if already auto-removed upon task deletion).
- **Failure Indicator & Action**: If `DeleteTemplate` returns `SMS.7111`, the task is still linked and must be deleted first.
