# Out of Scope

This skill manages Huawei Cloud **DDS** (Document Database Service) and **DCS** (Distributed Cache
Service) instances, and only the operations listed in `SKILL.md`:

- **DDS** — list/get instances, deployment analysis, create instance, add read-only node, add
  sharding node, create manual backup, delete instance.
- **DCS** — list/get instances, node information, security analysis, list config templates, create
  instance, create custom template, delete instance, restart/flush instance.

Any request outside that boundary is **not supported**. This page is the authoritative list of the
uncovered operations. When a request matches a row below, do not build or run a command for it;
decline the request, say clearly that the operation is outside this skill's scope, and point the
user to the substitute entry point listed for that row.

> Substitute entry points are user-facing navigation guidance only — a console path the user can
> follow, or the dedicated skill of the corresponding Huawei Cloud service when one is available in
> the user's environment. Console menu labels may differ slightly by region and console version.

## DDS Operations Not Covered

| # | Operation | Representative API / action | Substitute entry point (user navigation) |
|---|-----------|-----------------------------|------------------------------------------|
| 1 | Restart a DDS instance | `RestartInstance` (`dds:instance:restart`) | Huawei Cloud console → **Databases** → **Document Database Service (DDS)** → **Instances** → open the instance → **Restart** (or **More → Restart**). |
| 2 | Resize / change the specification of a DDS instance | `ResizeInstance` (`dds:instance:resize`) | Console → **DDS** → **Instances** → open the instance → **Change Specification** (instance details → specification change); select the target flavor and confirm the billing change. |
| 3 | Expand DDS disk capacity | volume expansion / `ResizeInstance` disk step | Console → **DDS** → **Instances** → open the instance → **Disk Expansion**; enter the new capacity and confirm. |
| 4 | Upgrade the DDS database version | minor/major version upgrade | Console → **DDS** → **Instances** → open the instance → **Upgrade** (version upgrade); follow the pre-upgrade checklist and compatibility notes shown there. |
| 5 | Restore a DDS backup to an instance | `RestoreInstance` | Console → **DDS** → **Backups** → select the backup → **Restore** → choose the target instance and confirm. |
| 6 | Delete a DDS backup | `BatchDeleteBackup` (`dds:backup:delete`) | Console → **DDS** → **Backups** → select the backup → **Delete**. |
| 7 | Modify DDS configuration parameters | `UpdateEntityConfiguration` | Console → **DDS** → **Instances** → open the instance → **Parameters** → edit values → **Save**; for reusable sets use **DDS → Parameter Groups**. |
| 8 | Manage DDS parameter groups | parameter-group create/copy/apply/reset | Console → **DDS** → **Parameter Groups** → create/copy/compare/apply or reset the group. |

## DCS Operations Not Covered

| # | Operation | Representative API / action | Substitute entry point (user navigation) |
|---|-----------|-----------------------------|------------------------------------------|
| 9 | Modify the DCS IP whitelist | `UpdateIpWhitelist` | Console → **Databases** → **Distributed Cache Service (DCS)** → **Instances** → open the instance → **Access Control / IP Whitelist** → edit the entries → **Save**. |
| 10 | Reset the DCS instance password | `UpdatePassword` | Console → **DCS** → **Instances** → open the instance → **Reset Password**; the new password must meet the Redis complexity rules. |
| 11 | Big key / hot key analysis for DCS | `BigKeyAnalysis` / `HotKeyAnalysis` | Console → **DCS** → **Instances** → open the instance → **Analysis** → **Big Key Analysis** or **Hot Key Analysis**, then start a scan. |
| 12 | Resize / change the specification of a DCS instance (including scale-up/scale-down) | `ResizeInstance` / specification change | Console → **DCS** → **Instances** → open the instance → **Change Specification**; pick the target flavor and confirm the billing change. |
| 13 | Expand DCS disk / shard capacity | capacity expansion | Console → **DCS** → **Instances** → open the instance → **Scale** / **Disk Expansion** (the available options vary by instance type). |
| 14 | Upgrade the DCS engine version | `UpgradeInstanceVersion` | Console → **DCS** → **Instances** → open the instance → **Upgrade**; follow the compatibility checks shown in the console. |

## Other Huawei Cloud Services Not Covered

| # | Service | Substitute entry point (user navigation) |
|---|---------|------------------------------------------|
| 15 | RDS (Relational Database Service) instance management | Console → **Databases** → **Relational Database Service (RDS)** → **Instances** (create, restart, resize, backup, restore, parameters). If a dedicated RDS service skill is available in your environment, switch to it for those operations. |
| 16 | GaussDB / GaussDB(for MySQL) instance management | Console → **Databases** → **GaussDB** → **Instances**. If a dedicated GaussDB service skill is available in your environment, switch to it for those operations. |
| 17 | GaussDB(for Mongo) / GaussDB(for Redis) management | Console → **Databases** → the **GaussDB(for Mongo)** or **GaussDB(for Redis)** service page → **Instances**. If a dedicated skill for that service is available in your environment, switch to it for those operations. |
| 18 | Any other Huawei Cloud service (ECS, VPC, OBS, IAM, …) | Console → open the service page for that resource and manage it there; if a dedicated skill for that service is available in your environment, switch to it for those operations. |

## How to Respond to an Out-of-Scope Request

1. State the boundary explicitly, for example: "**{requested operation}** is not supported by this
   skill, which covers only the DDS and DCS instance operations listed in its Capability Matrix."
2. Name the substitute entry from the tables above (console navigation, or the corresponding
   service's dedicated skill when the user has one).
3. Do not attempt the operation through an unrelated API, and do not fabricate a command for it.
