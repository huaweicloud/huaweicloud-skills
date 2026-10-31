# Risks and Impact of Single-to-HA Conversion (RDS for MySQL)

> This reference is presented to the user by the SKILL workflow (risk disclosure step) before any cloud operation.

## 1. Inherent Risks of a Single-Instance Deployment

A single instance uses a single database node deployment architecture. Compared with a primary/standby instance, it has the following inherent risks:

| Risk ID | Risk Item | Risk Description | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| R-001 | Single point of failure (SPOF) | A single instance deploys only one database node; when the node fails, the instance is unavailable and cannot recover automatically | High | Convert to a primary/standby instance as soon as possible |
| R-002 | No disaster recovery | No standby node to take over, no cross-AZ disaster recovery; does not meet high-availability business requirements | High | Convert to a primary/standby instance and select a different AZ |
| R-003 | Data reliability risk | Relies on single-node storage; hardware failure may cause data loss (an automatic backup mechanism mitigates the risk) | Medium | Enable the automatic backup policy and convert to primary/standby |
| R-004 | Uncontrollable RTO/RPO | After a single-node failure, the recovery time (RTO) and recovery point objective (RPO) depend on backup frequency and failure type and cannot be guaranteed | High | Convert to primary/standby for automatic failover |
| R-005 | Maintenance impact | System maintenance, patch updates, and similar operations may cause brief unavailability, with no standby node to serve traffic | Medium | Convert to primary/standby outside the maintenance window |

## 2. Capability Comparison: Single vs Primary/Standby

| Dimension | Single Instance | Primary/Standby Instance |
| --- | --- | --- |
| Deployment architecture | Single database node | One primary and one standby, classic high-availability architecture |
| Max tolerable failed nodes | 0 | 1 |
| Automatic failover | Not supported | Supported; the standby node takes over traffic quickly |
| Cross-AZ disaster recovery | Not supported | Supported (it is recommended to place the primary and standby in different AZs) |
| Data redundancy | No real-time redundancy | Primary/standby data synchronized in real time |
| RTO (recovery time objective) | Uncontrollable (depends on manual recovery) | Second-level automatic failover |
| RPO (recovery point objective) | Depends on backup frequency | Near zero (real-time sync) |
| Suitable scenarios | Development/testing, non-core business | Production, core business systems |

## 3. Operational Impact of Converting to Primary/Standby

| Impact | Description | Severity |
| --- | --- | --- |
| Primary instance business | The single-to-HA conversion is unrelated to read replicas and does not affect the primary instance or read replica business | No impact |
| Read replica business | Not affected by the conversion; read replicas continue to serve normally | No impact |
| Connection information | Does not change the instance connection information, including VPC, subnet, security group, private address, private domain name, and database port | No impact |
| Instance restart | The primary instance does not need to restart; it keeps serving during the conversion | No impact |
| CPU usage | Because the standby node must sync the primary node's full data, CPU usage may rise briefly | Minor impact |
| Conversion duration | Depends on the size of the data to be backed up; more data means a longer duration. The full flow (manual backup + single-to-HA conversion) typically takes about 10-20 minutes | Evaluate |
| Reversibility | RDS supports converting a single instance to primary/standby only; primary/standby cannot be converted back to single (irreversible) | Irreversible |

**Why CPU rises and what to expect**: During the single-to-HA conversion, the system must back up the primary node's full data and sync it to the newly created standby node. The primary node performs a full backup, which consumes extra CPU and I/O resources and may cause a brief CPU usage rise of 5%-15% (depending on data volume and instance flavor). It is recommended to run the conversion during a business low-peak period.

**Instance status during the conversion**: During the conversion, the instance status shows "Converting to Primary/Standby" (API status value: `MODIFYING INSTANCE TYPE`). You can track the background task progress in the task center. After the conversion completes, the instance status returns to "Normal" (`ACTIVE`) and the instance type shows "Primary/Standby" (`Ha`).

## 4. Cost Explanation

### 4.1 Billing Modes

| Billing Mode | Change Operation | Cost Impact |
| --- | --- | --- |
| Prepaid (monthly/yearly) | Single to primary/standby | After the change, pay the price difference based on the remaining time in the billing cycle (the SKILL automatically sends `is_auto_pay=true` and Huawei Cloud auto-charges the difference from the account — ensure the account balance is sufficient) |
| Pay-per-use (on-demand) | Single to primary/standby | After the change, billed hourly at the primary/standby instance price |

### 4.2 Prepaid Price-Difference Calculation

Price difference to pay = primary/standby instance price × remaining period - single instance price × remaining period
Remaining period = remaining days of each natural month / maximum days of that natural month

### 4.3 Other Costs

- **Storage cost**: A primary/standby instance stores 2 copies of the data (one for the primary node and one for the standby node), so storage capacity doubles. The storage price also rises because HA storage is billed at a higher rate than single storage (verified for 40 GB CLOUDSSD: about +60% monthly/yearly, +10% on-demand).
- **Backup cost**: The backup policy is unchanged after the conversion; backup storage is billed by the actual backup volume (manual backups consume the backup storage quota, and storage beyond the free quota is billed by volume).
- **Network cost**: Primary/standby sync within the same VPC generates no extra network cost; cross-AZ sync uses the private network and generates no public traffic cost.

## 5. Rollback Guidance

The single-to-HA conversion is **irreversible** (primary/standby cannot be converted back to single). To roll back, use one of the following approaches:

- **Option A (recommended)**: migrate data to a newly created single instance via DRS.
- **Option B**: restore a backup, or use mysqldump to export/import to a newly created single instance.

All rollback options require additional instance cost and data migration time. Evaluate business requirements fully before the conversion, decide carefully, and perform the operation during a business low-peak period.
