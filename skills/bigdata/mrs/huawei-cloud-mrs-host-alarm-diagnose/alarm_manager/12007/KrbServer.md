# KrbServer Process Fault (12007) Diagnosis

## Fault Impact

- KrbServer process fault may cause cluster Kerberos authentication failure, causing components to fail to run normally
- If the OMS built-in Kerberos (okerberos) process is faulty, the Manager management plane authentication is also affected

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
  +-- Process recovered -> Check accompanying alarms and krb5kdc logs to locate the historical fault cause
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
                    +-- krb5kdc log has FATAL/error -> Root cause 1/3
                    +-- checkservice log has fail -> Root cause 1
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
# Query KrbServer instance running status
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=KrbServer' \
  --json
```

```bash
# Query process status on the alarm node
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' \
  --json
```

> Look for `krb5kdc` and `kadmind` processes in the returned process list. If the process is missing or abnormal, the alarm is ongoing.

> KrbServer contains two types of instances:
> - **Cluster Kerberos** (KerberosServer/KerberosAdmin): processes are `krb5kdc` and `kadmind`
> - **OMS Kerberos** (okerberos): processes are also `krb5kdc` and `kadmind`

**Analysis**:

| Actual result | Conclusion | Next step |
|---------------|------------|-----------|
| krb5kdc/kadmind processes exist and status normal | Alarm recovered | Check accompanying alarms and krb5kdc logs |
| krb5kdc/kadmind processes missing | Alarm ongoing | Judge by alarm count |
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

#### 4.1 Browse krb5kdc Running Logs

> Determine which log group to collect based on the role name in the alarm location info:
> - **Cluster KerberosServer**: logs in `/var/log/Bigdata/kerberos/`
> - **OMS okerberos**: logs in `/var/log/Bigdata/okerberos/`

```bash
# Confirm the krb5kdc log file name
python manager_api_client.py -a get_log_filename \
  -p 'hostname=<node_name>' \
  -p 'category_name=krb5kdc' \
  -p 'path=/var/log/Bigdata/kerberos' \
  --json
```

```bash
# Browse the cluster KrbServer krb5kdc logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/kerberos/krb5kdc.log' \
  --json
```

```bash
# Browse the OMS Kerberos krb5kdc logs (when the alarm role is okerberos)
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/okerberos/oms-krb5kdc.log' \
  --json
```

> If the file name is uncertain or time filtering is needed, use the log search API:

```bash
# Search abnormal keywords in krb5kdc logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=FATAL' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=KrbServer:KrbServer:KerberosServer' \
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
| `FATAL` or `Cannot initialize` | KDC initialization failed, configuration or data file abnormal -> **Root cause located**: Root cause 1 |
| `Cannot find keytab` | keytab file missing -> **Root cause located**: Root cause 1 |
| `preauth` related errors | Pre-authentication abnormal, may affect authentication but not necessarily cause process fault |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |
| `Permission denied` | File permission issue -> **Root cause located**: Root cause 1 |

#### 4.2 Browse kadmind Logs

```bash
# Browse kadmind logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/kerberos/kadmind.log' \
  --json
```

```bash
# Search abnormal keywords in kadmind logs
python manager_api_client.py -a start_log_search \
  -p 'key_word=error' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=KrbServer:KrbServer:KerberosAdmin' \
  -p 'min_log_level=INFO' \
  --json
```

#### 4.3 Browse Kerberos Health Check/Monitor Logs

```bash
# Confirm the Kerberos service check log file name
python manager_api_client.py -a get_log_filename \
  -p 'hostname=<node_name>' \
  -p 'category_name=check-krb-availability' \
  -p 'path=/var/log/Bigdata/kerberos' \
  --json
```

```bash
# Browse Kerberos service check logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/kerberos/check-krb-availability.log' \
  --json
```

```bash
# Browse Kerberos service monitor logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/kerberos/krb_server_mon.log' \
  --json
```

> If the above APIs are all unavailable, use the `gather_log` API to collect a log package for analysis:

```bash
# Collect the KrbServer log package
python manager_api_client.py -a gather_log \
  -p 'cluster_name=<cluster_name>' \
  -p 'services=KrbServer:KerberosServer' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  --json
```

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `process is not exist` or `down` | Process not running -> **Root cause located**: Root cause 1 |
| `health check failed` | Health check failed, possibly encryption/decryption error -> **Root cause located**: Root cause 3 |
| `Cannot read kdc.conf` | Configuration file abnormal -> **Root cause located**: Root cause 1 |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |

---

## Common Root Causes and Repair Suggestions

### 1. Process Startup File, Configuration, or Data Abnormal

**Features**: krb5kdc log has `FATAL`, `Cannot initialize`, `Cannot find keytab`; health check log has `process is not exist`

**Repair suggestions**:
- Check whether the PID file exists: `cat /opt/huawei/Bigdata/tmp/krb-omm-kdc.pid` and `cat /opt/huawei/Bigdata/tmp/krb-omm-kadmind.pid`
- Check whether kdc.conf is complete: `cat /opt/huawei/Bigdata/FusionInsight_BASE_8.6.0.1/1_3_KerberosServer/etc/kdc.conf`
- Check whether the keytab file exists and has read permission
- Restart the KrbServer service via Manager UI

**Notes**:
- KrbServer restart causes brief Kerberos authentication interruption, affecting all cluster components
- Before restart, confirm whether it is a configuration issue to avoid repeated restarts

### 2. Node Resources Too High

**Features**: Node CPU/memory/load too high; many 12007 alarms present

**Repair suggestions**:
- Investigate whether high-CPU/high-memory processes are abnormal
- Clean up unnecessary processes to release resources
- After resources recover, wait 10 minutes to check whether the alarm clears

### 3. Node Encryption/Decryption Error

**Features**: Health check log has `health check failed`; krb5kdc log has encryption/decryption related errors

**Repair suggestions**:
- Check whether the node SCC (security component) is running normally
- Sync configuration via Manager UI and restart KrbServer
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
- Clean up krb5kdc rotated logs: `/var/log/Bigdata/kerberos/krb5kdc.log-*.gz`
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
