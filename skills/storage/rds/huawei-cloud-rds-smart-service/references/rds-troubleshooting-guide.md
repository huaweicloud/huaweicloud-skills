# RDS Troubleshooting Guide

## Common Fault Diagnosis Procedures

### 1. Instance Unavailable / Connection Failure

**Symptoms**: Cannot connect to RDS instance, connection timeout, refused connection.

**Diagnosis Steps**:
```bash
# Step 1: Check instance status
hcloud RDS ShowInstance --cli-region=cn-north-4 --instance_id={instance_id}

# Step 2: Check error logs for recent errors
hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z --level=ERROR

# Step 3: Validate connection
hcloud RDS ValidateInstanceConnection --cli-region=cn-north-4 --instance_id={instance_id}

# Step 4: Check replication status (for HA instances)
hcloud RDS ShowReplicationStatus --cli-region=cn-north-4 --instance_id={instance_id}
```

**Common Causes**:
- Security group rules blocking access
- Instance is in STORAGE_FULL or FAILOVER state
- EIP or VPC network configuration issues
- Database parameter misconfiguration (max_connections too low)

### 2. High CPU / Memory Usage

**Symptoms**: CPU utilization > 90%, memory usage > 85%, slow response.

**Diagnosis Steps**:
```bash
# Step 1: Query TOP SQL consuming most resources
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=20

# Step 2: Check slow logs
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z

# Step 3: Check wait events
hcloud RDS ListHistoryWaitEvents --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z

# Step 4: Check top objects (tables/indexes)
hcloud RDS ShowTopObjects --cli-region=cn-north-4 --instance_id={instance_id}

# Step 5: Check active sessions
hcloud RDS ListHistorySessions --cli-region=cn-north-4 --instance_id={instance_id}
```

**Resolution Actions**:
- Optimize TOP SQL statements (add indexes, rewrite queries)
- Kill problematic sessions: `CreateIntelligentKillSession`
- Resize instance to larger flavor: `StartResizeFlavorAction`
- Adjust parameters (e.g., increase `innodb_buffer_pool_size`)

### 3. Primary-Standby Replication Delay

**Symptoms**: Read replica lag, data inconsistency between primary and standby.

**Diagnosis Steps**:
```bash
# Step 1: Check replication status
hcloud RDS ShowReplicationStatus --cli-region=cn-north-4 --instance_id={instance_id}

# Step 2: Check error logs for replication errors
hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z --level=ERROR

# Step 3: Check slow logs (large transactions cause delay)
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z
```

**Resolution Actions**:
- Reduce large transaction size
- Optimize slow SQL on primary
- Consider failover if standby is more up-to-date: `StartFailover`
- Resize instance if replication bandwidth is insufficient

### 4. Disk Space Full

**Symptoms**: STORAGE_FULL status, cannot write data, auto-expansion not triggered.

**Diagnosis Steps**:
```bash
# Step 1: Check storage usage
hcloud RDS ShowStorageUsedSpace --cli-region=cn-north-4 --instance_id={instance_id}

# Step 2: Check auto-expansion policy
hcloud RDS ShowAutoEnlargePolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Step 3: Check volume info
hcloud RDS ListVolumeInfo --cli-region=cn-north-4 --instance_id={instance_id}
```

**Resolution Actions**:
- Enlarge disk volume: `StartInstanceEnlargeVolumeAction`
- Enable auto-expansion: `SetAutoEnlargePolicy`
- Clean up old data, logs, or temporary tables

### 5. Slow Query Performance

**Symptoms**: Query response time > 1s, high slow log count.

**Diagnosis Steps**:
```bash
# Step 1: List slow logs
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z

# Step 2: Analyze TOP SQL
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=10

# Step 3: Check top objects for hotspot tables
hcloud RDS ShowTopObjects --cli-region=cn-north-4 --instance_id={instance_id}
```

**Resolution Actions**:
- Add appropriate indexes on slow query columns
- Rewrite inefficient SQL (avoid SELECT *, use JOIN instead of subquery)
- Adjust parameters: `innodb_buffer_pool_size`, `sort_buffer_size`
- Consider read/write splitting for read-heavy workloads

### 6. Backup Failure

**Symptoms**: Backup task fails, no recent backups available.

**Diagnosis Steps**:
```bash
# Step 1: Check backup policy
hcloud RDS ShowBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Step 2: List recent backups
hcloud RDS ListBackups --cli-region=cn-north-4 --instance_id={instance_id}

# Step 3: Check error logs
hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z --level=ERROR

# Step 4: Check task status
hcloud RDS ListTasks --cli-region=cn-north-4 --start_time=2024-01-01T00:00:00Z --end_time=2024-01-01T23:59:59Z
```

**Resolution Actions**:
- Verify sufficient backup storage space
- Check backup time window (avoid peak hours)
- Create manual backup to test: `CreateManualBackup`
- Contact Huawei Cloud support if automated backup continues to fail

## Diagnostic Decision Tree

```
Instance Issue?
├── Connection Problem?
│   ├── Check instance status (ShowInstance)
│   ├── Check security group (ListErrorLogs)
│   └── Validate connection (ValidateInstanceConnection)
├── Performance Problem?
│   ├── High CPU? → ListTopSqls + ListHistoryWaitEvents
│   ├── Slow Query? → ListSlowLogs + ShowTopObjects
│   └── Disk Full? → ShowStorageUsedSpace + ShowAutoEnlargePolicy
├── HA Problem?
│   ├── Replication Delay? → ShowReplicationStatus
│   └── Failover Needed? → StartFailover (with confirmation)
├── Backup Problem?
│   ├── No Backups? → ShowBackupPolicy + ListBackups
│   └── Restore Needed? → ShowRecoveryTimeWindow + CreateRestoreInstance
└── Parameter Problem?
    ├── Show current params → ShowInstanceConfiguration
    └── Update params → UpdateInstanceConfiguration (with confirmation)
```
