# Identity and Access Management (IAM) Policies for Huawei Cloud SMS

This document defines the authentic, verified Identity and Access Management (IAM) system policies and custom least-privilege policies for Huawei Cloud Server Migration Service (SMS).

All action names and schemas in this document have been retrieved and validated against the Huawei Cloud IAM production service schema (`service_code=sms`).

---

## 1. System-Defined Policies

Huawei Cloud provides pre-configured system policies for SMS. Because SMS is a **Global service**, these policies are assigned at the global level.

| Policy Name | Scope | Type | Description |
|---|---|---|---|
| `SMS FullAccess` | Global | System-defined | Full management permissions for Server Migration Service. Allows managing source servers, creating/deleting migration tasks, configuring templates, and cutover operations. |
| `SMS ReadOnlyAccess` | Global | System-defined | Read-only permissions for Server Migration Service. Allows querying migration progress, server states, and migration task statistics. |

### Required Dependent Cloud Service Policies

Because host migration provisions and controls resources across compute, storage, and networking, an operator or migration user group requires permissions across dependent services:

| Service | Recommended System Policy | Reason for Dependency |
|---|---|---|
| **ECS** | `ECS FullAccess` or `ECS CommonOperations` | Create destination VMs, attach migration agent images, query instance states, and power-on post cutover. |
| **VPC** | `VPC FullAccess` or `VPC Administrator` | Query and bind VPC networks, target subnets, and security groups (ports 22, 8899, 8900). |
| **EVS** | `EVS FullAccess` or `EVS CommonOperations` | Allocate, format, attach, resize, and snapshot destination system and data volumes. |
| **IMS** | `IMS FullAccess` / `IMSReadOnlyPolicy` | Query OS images (`hcloud IMS ListImages`) to select target `image_id` for templates, and attach temporary agent bootstrap images. |
| **EIP** | `EIP FullAccess` (or ReadOnly) | Assign or bind Elastic Public IPs for internet-based migration channels. |
| **OBS** | `OBS OperateAccess` | Optional: Upload and collect migration diagnostics logs (`CollectLog`) or custom image storage. |
| **KMS** | `EVS KMSAccess` | Optional: Required only if destination target volumes require KMS encryption keys. |

---

## 2. Official SMS Action Reference

The following table lists the official action names supported by Huawei Cloud IAM for the `sms` service:

| IAM Action Name | Access Level | Description | Corresponding Operation |
|---|---|---|---|
| `sms:server:list` | List | Grants permission to list registered source servers | `ListServers` |
| `sms:server:get` | Read | Grants permission to query source server details and pre-checks | `ShowServer` |
| `sms:server:overview` | Read | Grants permission to query overall server migration statistics | `ShowOverview` |
| `sms:server:register` | Write | Grants permission to upload and register source server info | `RegisterServer` |
| `sms:server:update` | Write | Grants permission to update source server name | `UpdateServerName` |
| `sms:server:updateState` | Write | Grants permission to change source server replication state | `UpdateCopyState` |
| `sms:server:updateDiskInfo`| Write | Grants permission to update source server disk info | `UpdateDiskInfo` |
| `sms:server:delete` | Write | Grants permission to delete a registered source server | `DeleteServer` |
| `sms:server:batchDelete` | Write | Grants permission to batch delete source servers | `DeleteServers` |
| `sms:server:listErrors` | List | Grants permission to query source server error logs | `ListErrorServers` |
| `sms:server:listTask` | List | Grants permission to query migration task list | `ListTasks` |
| `sms:server:getTask` | Read | Grants permission to query migration task details and subtasks | `ShowTask` |
| `sms:server:createTask` | Write | Grants permission to create a migration replication task | `CreateTask` |
| `sms:server:updateTask` | Write | Grants permission to update task parameters | `UpdateTask` |
| `sms:server:manageTask` | Write | Grants permission to manage task lifecycle (start, stop, clear, restart) | `UpdateTaskStatus` |
| `sms:server:deleteTask` | Write | Grants permission to delete a migration task | `DeleteTask` |
| `sms:server:batchDeleteTask` | Write | Grants permission to batch delete migration tasks | `DeleteTasks` |
| `sms:server:updateTaskProgress` | Write | Grants permission to report task progress (Agent heartbeat) | `UpdateTaskSpeed` |
| `sms:server:getTaskSpeedLimit` | Read | Grants permission to query task speed throttling rules | `ShowsSpeedLimits` |
| `sms:server:updateTaskSpeedLimit` | Write | Grants permission to configure bandwidth speed throttling | `UpdateSpeed` |
| `sms:server:getTaskPassphrase` | Read | Grants permission to query task certificate passphrase | `ShowPassphrase` |
| `sms:server:unlock` | Write | Grants permission to unlock a target ECS (endpoint unpublished on API Gateway; returns APIGW.0101) | `UnlockTargetEcs` |
| `sms::checkNetwork` | Read | Grants permission to perform network & security group checks (endpoint unpublished on API Gateway; returns APIGW.0101) | `CheckNetAcl` |
| `sms:server:collectLog` | Write | Grants permission to trigger and upload task diagnostics log | `CollectLog` |
| `sms:server:getConsistencyCheckResult` | Read | Grants permission to query consistency check results | `ShowConsistencyResult` |
| `sms:server:updateConsistencyCheckResult`| Write | Grants permission to update consistency check results | `UpdateConsistencyResult` |
| `sms:template:create` | Write | Grants permission to create a target VM template | `CreateTemplate` |
| `sms:template:list` | List | Grants permission to list target VM templates | `ListTemplates` |
| `sms:template:get` | Read | Grants permission to query target VM template details | `ShowTemplate` |
| `sms:template:update` | Write | Grants permission to modify target VM template settings | `UpdateTemplate` |
| `sms:template:delete` | Write | Grants permission to delete a target VM template | `DeleteTemplate` |
| `sms:template:batchDelete` | Write | Grants permission to batch delete target VM templates | `DeleteTemplates` |
| `sms:template:getTargetPassword` | Read | Grants permission to query target VM template password | `ShowTargetPassword` |
| `sms:migproject:create` | Write | Grants permission to create migration projects | `CreateMigproject` |
| `sms:migproject:list` | List | Grants permission to list migration projects | `ListMigprojects` |
| `sms:migproject:get` | Read | Grants permission to query migration project details | `ShowMigproject` |
| `sms:migproject:update` | Write | Grants permission to update migration project settings | `UpdateMigproject` |
| `sms:migproject:delete` | Write | Grants permission to delete migration projects | `DeleteMigproject` |
| `sms::getConfig` | Read | Grants permission to query SMS agent configuration | `ShowConfig` |

---

## 3. Custom Least-Privilege Policy Statement

When enterprise compliance mandates granular authorization without granting broad `*FullAccess` roles, use the following custom policy definitions.

> [!NOTE]
> **Policy Version Format (`5.0` vs `1.1`)**:
> - Huawei Cloud modern identity policy documents use `"Version": "5.0"` (standard for IAM v5 and official system policies such as `SMSFullAccessPolicy` and `SMSReadOnlyPolicy`).
> - Classic IAM custom policy syntax uses `"Version": "1.1"` (used in legacy IAM v3 console templates).
> - Both versions share identical `Statement`, `Action`, and `Resource` structures. `"Version": "5.0"` is recommended for modern deployments.

### 3.1 Migration Operator Policy (Full Migration Execution)

This policy grants all actions required to inspect, configure, replicate, and cutover hosts to Huawei Cloud:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sms:server:list",
        "sms:server:get",
        "sms:server:overview",
        "sms:server:register",
        "sms:server:updateDiskInfo",
        "sms:server:updateState",
        "sms:server:listTask",
        "sms:server:getTask",
        "sms:server:createTask",
        "sms:server:updateTask",
        "sms:server:manageTask",
        "sms:server:updateTaskSpeedLimit",
        "sms:server:getTaskSpeedLimit",
        "sms:server:deleteTask",
        "sms:server:collectLog",
        "sms:template:list",
        "sms:template:get",
        "sms:template:create",
        "sms:template:update",
        "sms:template:delete",
        "sms:migproject:list",
        "sms:migproject:get"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:showServer",
        "ecs:cloudServers:create",
        "ecs:cloudServers:delete",
        "ecs:cloudServers:start",
        "ecs:cloudServers:stop",
        "ecs:cloudServers:attach",
        "ecs:cloudServers:detachVolume",
        "evs:volumes:create",
        "evs:volumes:get",
        "evs:volumes:list",
        "evs:volumes:delete",
        "evs:volumes:use",
        "evs:snapshots:delete",
        "vpc:vpcs:list",
        "vpc:vpcs:get",
        "vpc:subnets:list",
        "vpc:subnets:get",
        "vpc:securityGroups:list",
        "vpc:securityGroups:get",
        "ims:images:list",
        "ims:images:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

### 3.2 Migration Read-Only Auditor Policy (Inspection Only)

This policy allows auditing source servers, migration task progress, and pre-checks without permission to mutate resources or trigger cutover:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sms:server:list",
        "sms:server:get",
        "sms:server:overview",
        "sms:server:listErrors",
        "sms:server:listTask",
        "sms:server:getTask",
        "sms:server:getTaskSpeedLimit",
        "sms::checkNetwork",
        "sms:server:getConsistencyCheckResult",
        "sms:template:list",
        "sms:template:get",
        "sms:migproject:list",
        "sms:migproject:get",
        "ecs:cloudServers:list",
        "ecs:cloudServers:showServer",
        "vpc:vpcs:list",
        "vpc:subnets:list",
        "vpc:securityGroups:list",
        "evs:volumes:list",
        "ims:images:list",
        "ims:images:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

---

## 4. Credential Security Guidelines

- **Zero Hardcoding**: Never hardcode Access Key (AK) or Secret Key (SK) credentials in migration scripts, documentation, or configuration files.
- **Environment Resolution**: Use standard environment variables (`HUAWEI_ACCESS_KEY`, `HUAWEI_SECRET_KEY`) or existing authenticated KooCLI profiles (`~/.hcli/config.json`).
- **Temporary Credentials**: In automated CI/CD or orchestration workflows, leverage IAM Agency delegation with temporary security tokens (`SecurityToken`).
