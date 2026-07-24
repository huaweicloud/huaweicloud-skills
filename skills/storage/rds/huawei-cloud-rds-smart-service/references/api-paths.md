# RDS REST API Paths

Verified from `huaweicloudsdkrds` SDK source code (v3).

## Instance Management

| Operation | Method | Path |
|-----------|--------|------|
| List Instances | GET | `/v3/{project_id}/instances` |
| Show Instance | GET | `/v3/{project_id}/instances/{instance_id}` |
| Create Instance | POST | `/v3/{project_id}/instances` |
| Delete Instance | DELETE | `/v3/{project_id}/instances/{instance_id}` |
| Restart Instance | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Resize Flavor | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Enlarge Volume | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Reduce Volume | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Failover | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Set Read-Only | POST | `/v3/{project_id}/instances/{instance_id}/action` |
| Update Alias | PUT | `/v3/{project_id}/instances/{instance_id}` |
| List Flavors | GET | `/v3/{project_id}/flavors` |
| List Datastores | GET | `/v3/{project_id}/datastores` |
| Show Quotas | GET | `/v3/{project_id}/quotas` |

## Log Management

| Operation | Method | Path |
|-----------|--------|------|
| List Slow Logs | GET | `/v3/{project_id}/instances/{instance_id}/slowlog` |
| List Error Logs | GET | `/v3/{project_id}/instances/{instance_id}/errorlog` |
| List Error Logs (v3.1) | GET | `/v3.1/{project_id}/instances/{instance_id}/error-log` |
| Download Slowlog | POST | `/v3/{project_id}/instances/{instance_id}/slowlog/download` |
| Download Errorlog | POST | `/v3/{project_id}/instances/{instance_id}/errorlog/download` |
| List Audit Logs | GET | `/v3/{project_id}/instances/{instance_id}/auditlog` |
| Show Auditlog Policy | GET | `/v3/{project_id}/instances/{instance_id}/auditlog-policy` |
| Set Auditlog Policy | PUT | `/v3/{project_id}/instances/{instance_id}/auditlog-policy` |

## SQL Performance

| Operation | Method | Path |
|-----------|--------|------|
| List Top SQLs | GET | `/v3/{project_id}/instances/{instance_id}/top-sql` |
| List History Top SQLs | GET | `/v3/{project_id}/instances/{instance_id}/history-top-sql` |
| List History Wait Events | GET | `/v3/{project_id}/instances/{instance_id}/wait-events` |
| Show Top Objects | GET | `/v3/{project_id}/instances/{instance_id}/top-object` |
| Create SQL Limit | POST | `/v3/{project_id}/instances/{instance_id}/sql-limit` |

## Parameter Configuration

| Operation | Method | Path |
|-----------|--------|------|
| List Configurations | GET | `/v3/{project_id}/configurations` |
| Show Configuration | GET | `/v3/{project_id}/configurations/{config_id}` |
| Create Configuration | POST | `/v3/{project_id}/configurations` |
| Update Configuration | PUT | `/v3/{project_id}/configurations/{config_id}` |
| Delete Configuration | DELETE | `/v3/{project_id}/configurations/{config_id}` |
| Apply Configuration | PUT | `/v3/{project_id}/configurations/{config_id}/apply` |
| Show Instance Configuration | GET | `/v3/{project_id}/instances/{instance_id}/configurations` |
| Update Instance Configuration | PUT | `/v3/{project_id}/instances/{instance_id}/configurations` |
| Compare Configuration | GET | `/v3/{project_id}/configurations/compare` |

## Backup & Recovery

| Operation | Method | Path |
|-----------|--------|------|
| Show Backup Policy | GET | `/v3/{project_id}/instances/{instance_id}/backups/policy` |
| Set Backup Policy | PUT | `/v3/{project_id}/instances/{instance_id}/backups/policy` |
| List Backups | GET | `/v3/{project_id}/backups` |
| Create Manual Backup | POST | `/v3/{project_id}/backups` |
| Delete Manual Backup | DELETE | `/v3/{project_id}/backups/{backup_id}` |
| Show Backup Download Link | GET | `/v3/{project_id}/backups/{backup_id}` |
| Restore to New Instance | POST | `/v3/{project_id}/instances` (restore mode) |
| Restore to Existing | POST | `/v3/{project_id}/instances/{instance_id}/action` (restore) |
| Restore Tables | POST | `/v3/{project_id}/instances/{instance_id}/tables/recovery` |
| Show Recovery Time Window | GET | `/v3/{project_id}/instances/{instance_id}/recovery-time-window` |

## Diagnosis

| Operation | Method | Path |
|-----------|--------|------|
| Show Replication Status | GET | `/v3/{project_id}/instances/{instance_id}/replication/status` |
| List Instance Diagnosis | GET | `/v3/{project_id}/instances/{instance_id}/diagnosis` |
| List Instances Info Diagnosis | GET | `/v3/{project_id}/instances/info/diagnosis` |
| Create Intelligent Kill Session | POST | `/v3/{project_id}/instances/{instance_id}/kill-session` |
| Show Kill Session History | GET | `/v3/{project_id}/instances/{instance_id}/kill-session/history` |
| Show Second-Level Monitoring | GET | `/v3/{project_id}/instances/{instance_id}/second-level-monitoring` |
| Validate Connection | POST | `/v3/{project_id}/instances/{instance_id}/connection-validation` |

## Security

| Operation | Method | Path |
|-----------|--------|------|
| Set Security Group | POST | `/v3/{project_id}/instances/{instance_id}/security-group` |
| Switch SSL | POST | `/v3/{project_id}/instances/{instance_id}/ssl` |

## Tasks

| Operation | Method | Path |
|-----------|--------|------|
| List Tasks | GET | `/v3/{project_id}/tasks` |
| Show Task Detail | GET | `/v3/{project_id}/tasks/{task_id}` |

## API Base URLs by Region

| Region | Base URL |
|--------|----------|
| cn-north-4 (北京四) | `https://rds.cn-north-4.myhuaweicloud.com` |
| cn-north-1 (北京一) | `https://rds.cn-north-1.myhuaweicloud.com` |
| cn-east-3 (上海一) | `https://rds.cn-east-3.myhuaweicloud.com` |
| cn-south-1 (广州) | `https://rds.cn-south-1.myhuaweicloud.com` |
| ap-southeast-1 (香港) | `https://rds.ap-southeast-1.myhuaweicloud.com` |
