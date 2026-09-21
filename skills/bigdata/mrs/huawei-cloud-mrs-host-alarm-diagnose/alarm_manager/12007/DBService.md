# DBService Process Fault (12007) Diagnosis

## Fault Impact

- If all DBService processes are faulty, the database service is unavailable, data import and query functions cannot be provided, components that depend on the database service are abnormal, and database-related service operations fail
- If only a single DBService process is faulty in an active/standby scenario, DBService reliability decreases, the active node load increases, and service reliability is affected

## Possible Causes

1. DBService floating IP address does not exist
2. GaussDB related file permissions were modified, causing the process health check to fail
3. Database health check fails due to database password encryption/decryption failure
4. Node resources (CPU, memory, IO, load) too high
5. Disk space insufficient

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

## API Call Chain Dependencies

| Previous API | Return field | Next API | Parameter |
|--------------|--------------|----------|-----------|
| `get_instances` | `id`, `host.hostname`, `runningStatus` | `get_host_process` | `hostname` to confirm whether the process exists |
| `get_alarms` | alarm list | analysis | judge whether it is a node-level issue |
| `get_log_filename` | full log file path | `browse_log` | `file_name` |
| `start_log_search` | `task_id` | `get_log_search_progress` | `search_id` |

> The `file_name` parameter of `browse_log` must be the full path of the log file; relative paths or file names are not supported.

---

## Diagnosis Steps

### Step 1: Confirm Process Status and Alarm Scope

```bash
# Query current alarm list
python manager_api_client.py -a get_alarms -p 'status=1' --json
```

```bash
# Query DBService instance running status (returns runningStatus/haStatus)
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=DBService' \
  --json
```

```bash
# Query process status on the alarm node (returns processStatus/processId)
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' \
  --json
```

> Look for `gaussdb` related processes in the returned process list. If the process is missing or abnormal, the alarm is ongoing.

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
python manager_api_client.py -a get_alarms -p 'status=1' --json
```

```bash
# View node disk space
python manager_api_client.py -a get_host_resource \
  -p 'hostname=<node_name>' \
  --json
```

```bash
# View node system load and memory
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min,dev_swap_used_ratio' \
  --json
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
# Query DBService instance info, get the instance host and HA status
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=DBService' \
  --json
```

> The DBService floating IP is usually attached to the primary NIC as `bond0:DBS` or a similar alias. Example IP format: `8.5.235.182`. The floating IP can be confirmed from the alarm additional info or the instance info.

**Analysis**:

| Actual result | Conclusion | Next step |
|---------------|------------|-----------|
| Floating IP exists and can be pinged | Not a floating IP issue | 3.2 |
| Floating IP missing | Floating IP lost | **Root cause located**: Root cause 1 |
| Floating IP exists but unreachable | Network issue | Check network configuration |

#### 3.2 Check Disk Space

```bash
# View node resource info (disk usage)
python manager_api_client.py -a get_host_resource \
  -p 'hostname=<node_name>' \
  --json
```

```bash
# View disk related monitor metrics
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_disk_useage' \
  --json
```

**Analysis**:

| Phenomenon | Conclusion | Next step |
|------------|------------|-----------|
| ALM-12017 alarm present or disk usage > 85% | Disk space insufficient | **Root cause located**: Root cause 5 |
| Disk normal | Not a disk issue | 3.3 |

#### 3.3 Check Node Resources

```bash
# View CPU and memory usage
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min,dev_swap_used_ratio' \
  --json
```

| Phenomenon | Conclusion |
|------------|------------|
| Node CPU/memory too high | Resource bottleneck causes process unresponsive -> **Root cause located**: Root cause 4 |
| Resources normal | Continue log troubleshooting |

---

### Step 4: Deep Log Troubleshooting

#### 4.1 Browse DBService Health Check Logs

```bash
# Confirm the health check log file name
python manager_api_client.py -a get_log_filename \
  -p 'hostname=<node_name>' \
  -p 'category_name=dbservice_processCheck' \
  -p 'path=/var/log/Bigdata/dbservice/healthCheck' \
  --json
```

```bash
# Browse DBService health check logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/dbservice/healthCheck/dbservice_processCheck.log' \
  --json
```

> If the file name is uncertain or time filtering is needed, use the log search API:

```bash
# Search abnormal keywords in health check logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=failCount' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=DBService:DBService:DBServer' \
  -p 'min_log_level=INFO' \
  --json

# View search progress and results
python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' \
  --json
```

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `failCount` keeps increasing without reset | Health check keeps failing, process abnormal |
| `gaussDB status is abnormal` | gaussdb process abnormal |
| `floatip status is abnormal` | Floating IP abnormal -> Root cause 1 |
| `is not listened by gaussdb` | gaussdb port not listening, process not started |

#### 4.2 Browse GaussDB Running Logs

```bash
# Confirm the gaussdb log file name
python manager_api_client.py -a get_log_filename \
  -p 'hostname=<node_name>' \
  -p 'category_name=gaussdb' \
  -p 'path=/var/log/Bigdata/dbservice/DB' \
  --json
```

```bash
# Browse gaussdb running logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/dbservice/DB/gaussdb.log' \
  --json
```

> If `gaussdb.log` returns nothing or is rotated, try `gaussdb.log.1`, `gaussdb.log-*.gz`, etc., or use the log search API:

```bash
# Search abnormal keywords in gaussdb logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=FATAL' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=DBService:DBService:DBServer' \
  -p 'min_log_level=INFO' \
  --json
```

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `FATAL` or `PANIC` | Severe database error, process crashed -> **Root cause located**: Root cause 3 |
| `permission denied` | File permission issue -> **Root cause located**: Root cause 2 |
| `could not bind` | Port occupied or missing |
| `password authentication failed` | Password encryption/decryption failure -> **Root cause located**: Root cause 3 |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |
| `could not access file` | File missing or permission abnormal -> **Root cause located**: Root cause 2 |

#### 4.3 Browse DBService Script Logs (as needed)

```bash
# Browse DBService HA check logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/dbservice/scriptlog/checkHaStatus.log' \
  --json
```

```bash
# Search abnormal keywords in HA check logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=abnormal' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=DBService:DBService:DBServer' \
  -p 'min_log_level=INFO' \
  --json
```

> If the above APIs are all unavailable, use the `gather_log` API to collect a log package for analysis:

```bash
# Collect the DBService log package
python manager_api_client.py -a gather_log \
  -p 'cluster_name=<cluster_name>' \
  -p 'services=DBService:DBServer' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  --json
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
| `<cluster_name>` | Cluster name (required by gather_log API) | lw666 |
| `<alarm_time>` | Alarm occurrence time | 2026/09/02 10:00:00 GMT+08:00 |
| `<current_time>` | Current time (format: yyyy-MM-ddTHH:mm:ss) | 2026/09/02 11:00:00 GMT+08:00 |
| `<task_id>` | Log search task ID (from start_log_search) | — |
