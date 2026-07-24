# RDS Instance Daily Inspection Template

## Inspection Checklist

### 1. Instance Status Check
```bash
hcloud RDS ListInstances --cli-region=cn-north-4
```
- [ ] All instances in ACTIVE status
- [ ] No instances in FAILOVER or STORAGE_FULL state

### 2. Backup Verification
```bash
hcloud RDS ShowBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id}
hcloud RDS ListBackups --cli-region=cn-north-4 --instance_id={instance_id}
```
- [ ] Automated backup enabled
- [ ] Last backup within 24 hours
- [ ] Backup retention period adequate

### 3. Slow SQL Analysis
```bash
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date={today}T00:00:00Z --end_date={today}T23:59:59Z
```
- [ ] No new slow SQL patterns
- [ ] TOP SQL execution time within baseline

### 4. Error Log Review
```bash
hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date={today}T00:00:00Z --end_date={today}T23:59:59Z --level=ERROR
```
- [ ] No critical errors in last 24 hours
- [ ] No replication errors

### 5. Storage Check
```bash
hcloud RDS ShowStorageUsedSpace --cli-region=cn-north-4 --instance_id={instance_id}
```
- [ ] Disk usage below 80%
- [ ] Auto-expansion policy configured

### 6. Replication Health
```bash
hcloud RDS ShowReplicationStatus --cli-region=cn-north-4 --instance_id={instance_id}
```
- [ ] Primary-standby replication normal
- [ ] Replication delay within threshold
