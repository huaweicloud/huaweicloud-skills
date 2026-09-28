# Related SMS KooCLI Commands Quick Reference

This table provides a quick reference for common KooCLI operations used in Huawei Cloud Server Migration Service.

| Operation | Type | Syntax | Purpose |
|---|---|---|---|
| `ShowOverview` | Query | `hcloud SMS ShowOverview --cli-region={region}` | View count of servers across migration stages. |
| `ListServers` | Query | `hcloud SMS ListServers --cli-region={region} [--limit=N]` | List discovered/registered source servers. |
| `ShowServer` | Query | `hcloud SMS ShowServer --cli-region={region} --source_id={id}` | View detailed pre-check results, disks, and partition mapping for a server. |
| `ListVpcs/v3` (VPC) | Query | `hcloud VPC ListVpcs/v3 --cli-region={region} [--limit=N]` | Query target VPCs with pinned API version v3 to prevent unversioned preamble warning. |
| `KeystoneListProjects` (IAM) | Query | `hcloud IAM KeystoneListProjects --name={region} [--cli-query="projects[0].id"]` | Query project ID for the specified target region. |
| `KeystoneListAuthProjects` (IAM) | Query | `hcloud IAM KeystoneListAuthProjects` | List all projects authorized for the authenticated user/account. |
| `ListImages` (IMS) | Query | `hcloud IMS ListImages --cli-region={region} --status=active [--__imagetype=gold\|market] --__platform=<Platform>` | Query target OS images using `--__platform` (e.g. `Ubuntu`, `CentOS`, `Debian`, `EulerOS`, `Windows`). |
| `ListTasks` | Query | `hcloud SMS ListTasks --cli-region={region} [--limit=N]` | List ongoing and completed migration tasks. |
| `ShowTask` | Query | `hcloud SMS ShowTask --cli-region={region} --task_id={id}` | Check detailed progress, subtasks, and remaining migration time (`remain_seconds`). |
| `ListTemplates` | Query | `hcloud SMS ListTemplates --cli-region={region}` | Query target ECS deployment templates. |
| `ShowTemplate` | Query | `hcloud SMS ShowTemplate --cli-region={region} --id={id}` | Inspect template specifications (flavor, VPC, disk). |
| `ListMigprojects` | Query | `hcloud SMS ListMigprojects --cli-region={region}` | Query defined migration projects. |
| `CreateTemplate` | Mutate | `hcloud SMS CreateTemplate --cli-region={region} --cli-jsonInput="templates/create-template.json"` | Create target deployment template from JSON specification (skip for UEFI Windows). |
| `CreateTask` | Mutate | `hcloud SMS CreateTask --cli-region={region} --cli-jsonInput="templates/create-task.json"` (Linux template)<br>`hcloud SMS CreateTask --cli-region={region} --cli-jsonInput="templates/create-task-existing-server.json"` (UEFI Windows existing server) | Create and start a migration replication task from JSON specification (name: 4–20 chars). |
| `UpdateTaskStatus` | Mutate | `hcloud SMS UpdateTaskStatus --cli-region={region} --task_id={id} --operation={start\|stop\|clear\|restart}` | Control migration task state. Valid operations: `start\|stop\|clear\|restart\|test\|clone_test`. Use `--operation="clear"` for cutover finalization. |
| `UpdateSpeed` | Mutate | `hcloud SMS UpdateSpeed --cli-region={region} --task_id={id} --speed_limit.1.start=00:00 --speed_limit.1.end=24:00 --speed_limit.1.speed={speed}` | Adjust replication speed throttling limit (Mbit/s). |
| `ListSecurityGroupRules` | Query | `hcloud VPC ListSecurityGroupRules/v3 --cli-region={region} --security_group_id.1={sg_id}` | Verify inbound ports on target security group (22, 8899, 8900). |
| `ShowServer (ECS)` | Query | `hcloud ECS ShowServer --cli-region={region} --server_id={id}` | Inspect target ECS status, power state, and disk attachments. |
| `DeleteTask` | Mutate | `hcloud SMS DeleteTask --cli-region={region} --task_id={id}` | Remove a migration task (must be deleted BEFORE template). |
| `DeleteTemplate` | Mutate | `hcloud SMS DeleteTemplate --cli-region={region} --id={id}` | Remove a target template (delete AFTER task; safe to ignore `SMS.7101` if auto-deleted). |

## Key Operational Constraints

- **JSON Encapsulation (`--cli-jsonInput=<path>`)**:
  `CreateTemplate` and `CreateTask` require parameters wrapped inside a top-level `"body"` object.
- **Windows Backslash Double-Escaping**:
  KooCLI (v7.2.12) requires 4 backslashes for Windows paths and volume UUIDs in JSON files (e.g., `"name": "C:\\\\"`). If a future KooCLI update fixes this, revert to standard 2-backslash escaping (`"name": "C:\\"`). See `templates/create-task-windows.json`.
- **Network Mode Binding**:
  - **Public**: Template sets `publicip` with 300M bandwidth; Task sets `"use_public_ip": true, "migration_ip": ""`.
  - **Private**: Template sets `"publicip": {}`; Task sets `"use_public_ip": false, "migration_ip": "{target_private_ip}"`.
- **Deletion Order**:
  Always delete Task first, then Template (avoids `SMS.7111`; ignore `SMS.7101` if already auto-deleted).
