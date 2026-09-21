# DBService Process Fault (12007) Diagnosis

## Fault Impact

- If all DBService processes are faulty, the database service is unavailable, data import and query functions cannot be provided, components that depend on the database service are abnormal, and database-related service operations fail
- If only a single DBService process is faulty in an active/standby scenario, DBService reliability decreases, the active node load increases, and service reliability is affected

## Possible Causes

1. DBService floating IP address does not exist
2. GaussDB related file permissions were modified, causing the process health check to fail
3. Database health check fails due to database password encryption/decryption failure
4. Node resources (CPU, memory, IO, load) are too high
5. Disk space is insufficient

## Diagnosis Flow

```
Step 1: Confirm process status and alarm scope
  |
  +-- Process recovered -> Check accompanying alarms and historical logs to locate crash cause
  |
  +-- Process abnormal/missing
        |
        +-- Many 12007 alarms in the same period -> Step 2: Node-level troubleshooting
        +-- Single/few alarms -> Step 3: Single instance troubleshooting
              |
              +-- Floating IP abnormal -> Root cause 1
              +-- File permission abnormal -> Root cause 2
              +-- Disk space insufficient -> Root cause 5
              +-- Resources too high -> Root cause 4
              +-- Not located -> Step 4: Deep log troubleshooting
                    |
                    +-- gaussdb log has FATAL/PANIC -> Root cause 3
                    +-- healthCheck log has failCount anomaly -> Root cause 2/3
                    +-- Not located -> Suggest collecting logs and contacting technical support
```

## Diagnosis Steps

### Step 1: Confirm Process Status and Alarm Scope

```bash
# View the omm process tree on the node to confirm whether the gaussdb process exists
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

```bash
# View instance running status (Manager API proxy, returns runningStatus/haStatus)
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services/DBService/instances'
```

```bash
# View process status (Manager API proxy, returns processStatus/processId)
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/hosts/<node_name>/processes'
```

**Analysis**:

| Actual result | Conclusion | Next step |
|---------------|------------|-----------|
| gaussdb process exists and status normal | Alarm recovered, investigate historical cause | Check accompanying alarms and gaussdb logs |
| gaussdb process missing or status abnormal | Alarm ongoing | Judge by alarm count |
| Many 12007 alarms in the same period | Possibly a node-level issue | Step 2 |
| Single/few alarms | Single instance fault | Step 3 |

---

### Step 2: Node-Level Troubleshooting

When many 12007 alarms are concentrated on the same host in the same period, check the host itself first:

```bash
# Query host alarms, check for ALM-12006 NodeAgent process exception
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/alarms?status=1'
```

```bash
# View node disk space
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

```bash
# View node system load and memory
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=memory-usage' \
  -p 'node_name=<node_name>'
```

| Phenomenon | Conclusion |
|------------|------------|
| ALM-12006 alarm present | NodeAgent exception causes health check failure, handle 12006 first |
| Disk usage > 85% | Disk space insufficient, clean up disk first |
| Node load extremely high | Resource bottleneck causes process unresponsive, handle resource issue first |
| Node normal | Process issue itself, go to Step 3 |

---

### Step 3: Single Instance Troubleshooting

#### 3.1 Check Floating IP Address

DBService uses a floating IP to provide high availability; a missing floating IP causes process fault.

```bash
# View node network interface info to confirm whether the floating IP exists
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-interface-info' \
  -p 'node_name=<node_name>'
```

```bash
# Query DBService instance info, get the floating IP and service IP
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services/DBService/instances'
```

> The DBService floating IP is usually attached to the primary NIC as `bond0:DBS` or a similar alias. Example IP format: `8.5.235.182`.

**Analysis**:

| Actual result | Conclusion | Next step |
|---------------|------------|-----------|
| Floating IP exists and can be pinged | Not a floating IP issue | 3.2 |
| Floating IP missing | Floating IP lost | **Root cause located**: Root cause 1 |
| Floating IP exists but unreachable | Network issue | Check network configuration |

#### 3.2 Check Disk Space

```bash
# View disk space and IO
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-io' \
  -p 'node_name=<node_name>'
```

**Analysis**:

| Phenomenon | Conclusion | Next step |
|------------|------------|-----------|
| ALM-12017 alarm present or disk usage > 85% | Disk space insufficient | **Root cause located**: Root cause 5 |
| Disk normal | Not a disk issue | 3.3 |

#### 3.3 Check Node Resources

```bash
# View CPU and memory usage
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=high-cpu-processes' \
  -p 'node_name=<node_name>'
```

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=high-memory-process' \
  -p 'node_name=<node_name>'
```

| Phenomenon | Conclusion |
|------------|------------|
| Node CPU/memory too high | Resource bottleneck causes process unresponsive -> **Root cause located**: Root cause 4 |
| Resources normal | Continue log troubleshooting |

---

### Step 4: Deep Log Troubleshooting

#### 4.1 Collect DBService Health Check Logs

```bash
# Collect DBService health check logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/healthCheck' \
  -p 'log_file_name=dbservice_processCheck*' \
  -p 'keywords=["ERROR","WARN","fail","FAIL","abnormal"]' \
  -p 'log_type=local'
```

> The log time format is `[2026-09-02 09:45:27]`, supported by default, no `time_pattern` needed.

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `failCount` keeps increasing without reset | Health check keeps failing, process abnormal |
| `gaussDB status is abnormal` | gaussdb process abnormal |
| `floatip status is abnormal` | Floating IP abnormal -> Root cause 1 |
| `is not listened by gaussdb` | gaussdb port not listening, process not started |

#### 4.2 Collect GaussDB Running Logs

```bash
# Collect gaussdb running logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/DB' \
  -p 'log_file_name=gaussdb.log*' \
  -p 'keywords=["FATAL","PANIC","ERROR","could not","permission","denied"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^\\[([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||ymdHMS'
```

> The gaussdb log time format is `[2026-09-02 09:48:46.896 CST]`; pass `time_pattern` to match the `[YYYY-MM-DD HH:MM:SS` format.

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `FATAL` or `PANIC` | Severe database error, process crashed -> **Root cause located**: Root cause 3 |
| `permission denied` | File permission issue -> **Root cause located**: Root cause 2 |
| `could not bind` | Port occupied or missing |
| `password authentication failed` | Password encryption/decryption failure -> **Root cause located**: Root cause 3 |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |
| `could not access file` | File missing or permission abnormal -> **Root cause located**: Root cause 2 |

#### 4.3 Collect DBService Script Logs (as needed)

```bash
# Collect DBService HA check logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/scriptlog' \
  -p 'log_file_name=checkHaStatus*' \
  -p 'keywords=["ERROR","FAIL","abnormal","failover","switch"]' \
  -p 'log_type=local'
```

```bash
# Collect DBService database read-only alarm logs (if database_readonly_alarm.log exists)
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/scriptlog' \
  -p 'log_file_name=database_readonly_alarm*' \
  -p 'keywords=["readonly","ERROR","fail"]' \
  -p 'log_type=local'
```

---

## Common Root Causes and Repair Suggestions

### 1. Floating IP Address Missing

**Features**: Health check log shows `floatip status is abnormal`; floating IP not found on the NIC

**Repair suggestions**:
- Restart the DBService service in the Manager UI; the floating IP is re-attached automatically after restart
- If the floating IP still does not exist after restart, check NIC configuration and HA status

**Notes**:
- The floating IP is the basis of DBService high availability; IP loss causes active/standby switchover failure
- Restarting DBService briefly affects upper-layer services that depend on the database

### 2. GaussDB File Permission Abnormal

**Features**: gaussdb log has `permission denied`; files not owned by `omm:wheel` exist under `/srv/BigData/dbdata_service`

**Repair suggestions**:
- Run as omm user: `chown omm:wheel <fileName>` to repair file ownership
- Check permissions of `/srv/BigData/dbdata_service/data` and its subdirectories

**Notes**:
- After permission repair, wait 5 minutes for the health check to re-detect
- Do not use recursive `-R` modification; it may affect special permissions of subdirectories

### 3. Database Password Encryption/Decryption Failure

**Features**: gaussdb log has `password authentication failed` or `FATAL: password authentication failed for user`

**Repair suggestions**:
- Check whether the database password configured for DBService in Manager is correct
- Sync configuration via Manager UI and restart DBService
- If the key file is corrupted, contact technical support to regenerate the key

### 4. Node Resources Too High

**Features**: Node CPU/memory/load too high; many 12007 alarms present

**Repair suggestions**:
- Investigate whether high-CPU/high-memory processes are abnormal
- Clean up unnecessary processes to release resources
- After resources recover, wait 5 minutes to check whether the alarm clears

### 5. Disk Space Insufficient

**Features**: ALM-12017 alarm present; disk usage > 85%; gaussdb log has `No space left on device`

**Repair suggestions**:
- Clean up log files and temporary files (use `> file` to empty first, then delete)
- Clean up gaussdb rotated logs: `/var/log/Bigdata/dbservice/DB/gaussdb.log-*.gz`
- Expand the disk

## Variable Description

| Variable | Description | Example |
|----------|-------------|---------|
| `<cluster_id>` | MRS cluster ID | fd04c789-39d4-4847-8fc9-4572fec9414f |
| `<node_name>` | Alarm node name | 8-5-235-6 |
| `<alarm_time>` | Alarm occurrence time | 2026/09/02 10:00:00 GMT+08:00 |
