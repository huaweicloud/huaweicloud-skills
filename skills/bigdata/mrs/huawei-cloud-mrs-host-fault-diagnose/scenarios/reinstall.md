# Reinstall Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Old Component Data Backup Check
  │
  ├─ Step 2: Old Component Cleanup Check
  │
  ├─ Step 3: Reinstall Execution Check
  │
  └─ Step 4: Post-Reinstall Verification
```

## Step 1: Old Component Data Backup Check

**Goal**: Confirm whether data backup and configuration backup before reinstall were successfully completed, avoiding data loss during the reinstall process.

### 1.1 Backup Execution Log Check

Check the Controller and NodeAgent logs for backup operation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","backup","backupData","backupConfig","ERROR","fail","exception"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

Check the NodeAgent script logs for backup related content:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","backup","backupData","backupConfig","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 1.2 Backup Directory Verification

Based on the `data directory` and `backup directory` in the component config file, confirm whether backup files have been generated.
- Check whether the backup directory exists and is non-empty
- Check whether the backup timestamp is consistent with the reinstall operation time

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Backup failed | Insufficient disk space or permission error | Check backup directory disk space and permissions |
| Backup file not found | Backup script not executed or failed | Re-execute backup operation |
| Permission denied | Backup directory permission abnormal | Check backup directory owner and permissions |
| Config backup failed | Configuration file occupied or path error | Ensure component is stopped before backing up configuration |

---

## Step 2: Old Component Cleanup Check

**Goal**: Confirm that old component processes, residual files, and data directories have been correctly cleaned up, avoiding conflicts during reinstall.

### 2.1 Residual Process Check

Check whether the target node still has residual old component processes (should have been stopped before reinstall):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file. If the process still exists, the stop operation was not completed.

### 2.2 Residual Port Check

Check whether the old component port is still occupied (should have been released before reinstall):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

### 2.3 HA Resource Status Check (HA components only)

HA must be stopped before reinstall; check whether HA resources have been correctly released:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 2.4 Cleanup Execution Log Check

Check the NodeAgent script logs for cleanup operation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","clean","cleanup","remove","uninstall","delete","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Process still exists | Stop operation incomplete or process zombie | Manually kill residual processes and retry |
| Port still occupied | Process not fully exited | Confirm process has stopped, wait for port release |
| HA resource not released | HA not stopped before reinstall | Stop HA (ha_monitor, ha.bin) before reinstall |
| Cleanup script failed | Files occupied or insufficient permissions | Check file occupation and permissions |
| Data directory residual | Cleanup script not executed or skipped | Manually confirm data directory status |

---

## Step 3: Reinstall Execution Check

**Goal**: Confirm whether the reinstall operation's execution chain is normal at the Controller and NodeAgent levels.

### 3.1 Controller Reinstall Log Check

Check the Controller logs for reinstall operation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","reinstall","install","package","distribute","extract","ERROR","failed","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 3.2 NodeAgent Execution Log Check

Check the NodeAgent logs for reinstall execution records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","reinstall","ProcessAction","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 3.3 NodeAgent Script Execution Log Check

Check the NodeAgent script logs for reinstall script execution records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","reinstall","install","config","genConfig","restore","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 3.4 Configuration Restore Check

Check the NodeAgent script logs for configuration restore related records, confirming whether the backed-up configuration files have been correctly restored:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","restore","restoreConfig","restoreData","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Package not found | Installation package not distributed to node | Check packages directory, redistribute |
| Extract failed | Insufficient disk space or corrupted package | Clean up disk, verify SHA256 |
| Config restore failed | Backup configuration file missing or format error | Check backup directory configuration file integrity |
| Data restore failed | Backup data corrupted or path error | Verify backup integrity, re-restore |
| Permission denied | Installation directory or data directory permission abnormal | Fix directory permissions |
| HA rebuild failed | HA configuration missing or active/standby status abnormal | Check HA configuration file and rebuild |

---

## Step 4: Post-Reinstall Verification

**Goal**: Confirm that component processes, ports, data integrity, and HA status are all normal after reinstall.

### 4.1 Process and Port Verification

After reinstall, the component should auto-start; check whether processes exist and ports are listening:

```bash
# Process check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'

# Port check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

### 4.2 Data Integrity Verification

Check the component logs for data integrity verification records after data restore:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception","fail","FATAL","PANIC","corrupt","inconsistent"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 4.3 HA Status Verification (HA components only)

HA must be rebuilt after reinstall; check whether HA resource status is normal:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 4.4 Network Connectivity Verification

Check network connectivity between the reinstalled node and other cluster nodes:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-connectivity-test' \
  -p 'node_name=<node_name>'
```

### 4.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Reinstall` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)
- OMM process tree → `collect_alarm_node_res_data` (omm-process-tree)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Old data not cleaned | Residual processes or port occupation | Manually clean up residual processes and files, then retry reinstall |
| Backup failed | Backup directory empty or logs have backup fail | Fix backup directory permissions/space, re-backup |
| HA not stopped before reinstall | HA resource not released, reinstall logs have HA conflict | Stop HA (ha_monitor, ha.bin) before reinstall |
| Configuration not restored | Script logs have restoreConfig fail | Check backup configuration file integrity, manually restore |
| Data directory permissions changed | Component start failed after reinstall, logs have Permission denied | Fix data directory permissions (refer to component config file) |
| Data restore incomplete | Component logs have corrupt/inconsistent | Verify backup integrity, re-restore data |
| Insufficient disk space | disk-space check shows ≥85% | Clean up disk space, then retry reinstall |
| Installation package corrupted | Controller logs have Checksum mismatch | Re-download installation package and verify SHA256 |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Reinstall target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | e.g., gaussdb, ha_monitor |
| <port_number> | Component config file | e.g., 20013, 20015 |
| <log_directory> | Component config file | Component runtime log directory |
| <log_file_name> | Component config file | Component log file name pattern |
