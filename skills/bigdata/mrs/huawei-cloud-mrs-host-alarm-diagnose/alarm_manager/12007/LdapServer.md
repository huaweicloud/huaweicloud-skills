# LdapServer Process Fault (12007) Diagnosis

## Fault Impact

- LdapServer process fault may cause cluster Kerberos authentication failure, causing component services to fail to run normally
- OS user cache synchronization may be abnormal, causing component services to fail to run normally
- If the OMS built-in LdapServer (oldap) process is faulty, the Manager management plane authentication is also affected

## Possible Causes

1. Process startup file, configuration, or data abnormal
2. Node resources (CPU, memory, IO, load) too high
3. Node encryption/decryption error causes health check failure and cannot auto-recover
4. ALM-12040 OS entropy insufficient
5. Disk space insufficient

## Diagnosis Flow

```
Step 1: Confirm process status and alarm scope
  |
  +-- Process recovered -> Check accompanying alarms and ldapserver logs to locate the historical fault cause
  |
  +-- Process abnormal/missing
        |
        +-- Many 12007 alarms in the same period -> Step 2: Node-level troubleshooting
        +-- Single/few alarms -> Step 3: Single instance troubleshooting
              |
              +-- ALM-12040 present -> Root cause 4
              +-- Disk space insufficient -> Root cause 5
              +-- Resources too high -> Root cause 2
              +-- Not located -> Step 4: Deep log troubleshooting
                    |
                    +-- ldapserver log has FATAL/error -> Root cause 1/3
                    +-- chk_service log has fail -> Root cause 1
                    +-- Not located -> Suggest collecting logs and contacting technical support
```

## API Call Chain Dependencies

| Previous API | Return field | Next API | Parameter |
|--------------|--------------|----------|-----------|
| `get_instances` | `id`, `host.hostname`, `runningStatus` | `get_host_process` | `hostname` to confirm whether the process exists |
| `get_alarms` | alarm list | analysis | judge whether ALM-12040 exists |
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
# Query LdapServer instance running status
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=LdapServer' \
  --json
```

```bash
# Query process status on the alarm node
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' \
  --json
```

> Look for the `slapd` process in the returned process list. If the process is missing or abnormal, the alarm is ongoing.

> LdapServer contains two types of instances:
> - **Cluster LdapServer** (SlapdServer): process is `slapd`, listens on `ldaps://<node IP>:21780`
> - **OMS LdapServer** (oldap): process is `slapd`, listens on `ldaps://<OMS floating IP>:21750`

**Analysis**:

| Actual result | Conclusion | Next step |
|---------------|------------|-----------|
| slapd process exists and status normal | Alarm recovered | Check accompanying alarms and ldapserver logs |
| slapd process missing or status abnormal | Alarm ongoing | Judge by alarm count |
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
# View node system load
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' \
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

#### 3.1 Check Accompanying Alarms

```bash
# Query current alarm list, check for ALM-12040 OS entropy insufficient
python manager_api_client.py -a get_alarms -p 'status=1' --json
```

Check whether an `ALM-12040` alarm exists in the returned results:
- **Yes**: Handle the 12040 alarm first, wait 10 minutes after clearing to see if 12007 recovers -> **Root cause located**: Root cause 4
- **No**: Continue to 3.2

#### 3.2 Check Disk Space

```bash
# View node resource info (disk usage)
python manager_api_client.py -a get_host_resource \
  -p 'hostname=<node_name>' \
  --json
```

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
| Node CPU/memory too high | Resource bottleneck causes process unresponsive -> **Root cause located**: Root cause 2 |
| Resources normal | Continue log troubleshooting |

---

### Step 4: Deep Log Troubleshooting

#### 4.1 Browse LdapServer Service Check Logs

> Determine which log group to collect based on the role name in the alarm location info:
> - **Cluster LdapServer** (SlapdServer): logs in `/var/log/Bigdata/ldapserver/`
> - **OMS LdapServer** (oldap): logs in `/var/log/Bigdata/oldapserver/`

```bash
# Confirm the LdapServer service check log file name
python manager_api_client.py -a get_log_filename \
  -p 'hostname=<node_name>' \
  -p 'category_name=ldapserver_chk_service' \
  -p 'path=/var/log/Bigdata/ldapserver' \
  --json
```

```bash
# Browse the cluster LdapServer service check logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/ldapserver/ldapserver_chk_service.log' \
  --json
```

> If the file name is uncertain or time filtering is needed, use the log search API:

```bash
# Search abnormal keywords in LdapServer service check logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=fail' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=LdapServer:LdapServer:SlapdServer' \
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
| `chk service successfully` | Service normal, possibly transient fault |
| `chk service fail` or `not available` | Service check failed -> **Root cause located**: Root cause 1 |
| `process is not exist` or `slapd not running` | slapd process not running -> **Root cause located**: Root cause 1 |
| `health check failed` | Health check failed, possibly encryption/decryption error -> **Root cause located**: Root cause 3 |
| `cannot connect to` | slapd port not listening or network abnormal -> **Root cause located**: Root cause 1 |

#### 4.2 Browse LdapServer Startup Logs (as needed)

```bash
# Browse LdapServer startup logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/ldapserver/ldapserver_start.log' \
  --json
```

```bash
# Search abnormal keywords in startup logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=start fail' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=LdapServer:LdapServer:SlapdServer' \
  -p 'min_log_level=INFO' \
  --json
```

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `start successfully` | Process started normally in the past |
| `start fail` or `cannot start` | Process failed to start -> **Root cause located**: Root cause 1 |
| `Permission denied` | File permission issue -> **Root cause located**: Root cause 1 |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |
| `cannot read slapd.conf` | Configuration file abnormal -> **Root cause located**: Root cause 1 |

#### 4.3 Browse LdapServer Monitor/Metric Logs (as needed)

```bash
# Browse LdapServer metric collection logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/ldapserver/ldapserver_metric_collect.log' \
  --json
```

> If the above APIs are all unavailable, use the `gather_log` API to collect a log package for analysis:

```bash
# Collect the LdapServer log package
python manager_api_client.py -a gather_log \
  -p 'cluster_name=<cluster_name>' \
  -p 'services=LdapServer:SlapdServer' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  --json
```

---

## Common Root Causes and Repair Suggestions

### 1. Process Startup File, Configuration, or Data Abnormal

**Features**: Service check log shows `chk service fail`; startup log shows `start fail`; slapd process missing

**Repair suggestions**:
- Check whether the slapd process is alive: `ps aux | grep slapd | grep -v grep`
- Check whether the slapd port is listening: `ss -tlnp | grep slapd`
- Check whether slapd.conf is complete
- Restart the LdapServer service via Manager UI

**Notes**:
- LdapServer restart causes brief LDAP authentication interruption
- Cluster LdapServer listens on port 21780, OMS LdapServer listens on port 21750

### 2. Node Resources Too High

**Features**: Node CPU/memory/load too high; many 12007 alarms present

**Repair suggestions**:
- Investigate whether high-CPU/high-memory processes are abnormal
- Clean up unnecessary processes to release resources
- After resources recover, wait 10 minutes to check whether the alarm clears

### 3. Node Encryption/Decryption Error

**Features**: Health check log has `health check failed`; no clear startup/configuration error

**Repair suggestions**:
- Check whether the node SCC (security component) is running normally
- Sync configuration via Manager UI and restart LdapServer
- If the encryption/decryption component cannot auto-recover, contact technical support

### 4. OS Entropy Insufficient

**Features**: ALM-12040 alarm present

**Repair suggestions**:
- Clear the alarm per the ALM-12040 alarm handling guide
- Wait 10 minutes after clearing to see if the 12007 alarm recovers

### 5. Disk Space Insufficient

**Features**: ALM-12017 alarm present; disk usage > 85%

**Repair suggestions**:
- Clean up log files and temporary files (use `> file` to empty first, then delete)
- Clean up ldapserver rotated logs: `/var/log/Bigdata/ldapserver/ldapserver_chk_service_*.gz`
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
