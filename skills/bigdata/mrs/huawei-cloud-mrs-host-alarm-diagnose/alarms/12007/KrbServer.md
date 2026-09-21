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

## Diagnosis Steps

### Step 1: Confirm Process Status and Alarm Scope

```bash
# View the omm process tree on the node to confirm whether krb5kdc/kadmind processes exist
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

```bash
# View instance running status (Manager API proxy)
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services/KrbServer/instances'
```

```bash
# View process status (Manager API proxy)
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/hosts/<node_name>/processes'
```

> KrbServer contains two types of instances:
> - **Cluster Kerberos** (KerberosServer/KerberosAdmin): processes are `krb5kdc` and `kadmind`, PID files are `/opt/huawei/Bigdata/tmp/krb-omm-kdc.pid` and `/opt/huawei/Bigdata/tmp/krb-omm-kadmind.pid`
> - **OMS Kerberos** (okerberos): processes are also `krb5kdc` and `kadmind`, PID files are `/opt/huawei/Bigdata/om-server/tmp/krb-oms-omm-kdc.pid` and `/opt/huawei/Bigdata/om-server/tmp/krb-oms-omm-kadmind.pid`

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
# View node system load
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
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

#### 3.1 Check Accompanying Alarms

```bash
# Query current alarm list, check for ALM-12040 OS entropy insufficient
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/alarms?status=1'
```

Check whether an `ALM-12040` alarm exists in the returned results:
- **Yes**: Handle the 12040 alarm first, wait 10 minutes after clearing to see if 12007 recovers -> **Root cause located**: Root cause 4
- **No**: Continue to 3.2

#### 3.2 Check Disk Space

```bash
# View disk space
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

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
| Node CPU/memory too high | Resource bottleneck causes process unresponsive -> **Root cause located**: Root cause 2 |
| Resources normal | Continue log troubleshooting |

---

### Step 4: Deep Log Troubleshooting

#### 4.1 Collect krb5kdc Running Logs

> Determine which log group to collect based on the role name in the alarm location info:
> - **Cluster KerberosServer**: logs in `/var/log/Bigdata/kerberos/`
> - **OMS okerberos**: logs in `/var/log/Bigdata/okerberos/`

```bash
# Collect cluster KrbServer krb5kdc logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/kerberos' \
  -p 'log_file_name=krb5kdc.log*' \
  -p 'keywords=["FATAL","error","failed","Cannot","aborted","preauth"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^([A-Za-z]{3}) +([0-9]{1,2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||bdHMS'
```

> The krb5kdc log time format is `Sep 02 09:48:35` (month day hour:minute:second); pass `time_pattern` to match.

```bash
# Collect OMS Kerberos krb5kdc logs (when the alarm role is okerberos)
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/okerberos' \
  -p 'log_file_name=oms-krb5kdc.log*' \
  -p 'keywords=["FATAL","error","failed","Cannot","aborted"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^([A-Za-z]{3}) +([0-9]{1,2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||bdHMS'
```

**Analysis**:

| Log keyword | Conclusion |
|-------------|------------|
| `FATAL` or `Cannot initialize` | KDC initialization failed, configuration or data file abnormal -> **Root cause located**: Root cause 1 |
| `Cannot find keytab` | keytab file missing -> **Root cause located**: Root cause 1 |
| `preauth` related errors | Pre-authentication abnormal, may affect authentication but not necessarily cause process fault |
| `No space left on device` | Disk full -> **Root cause located**: Root cause 5 |
| `Permission denied` | File permission issue -> **Root cause located**: Root cause 1 |

#### 4.2 Collect kadmind Logs

```bash
# Collect kadmind logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/kerberos' \
  -p 'log_file_name=kadmind*' \
  -p 'keywords=["FATAL","error","failed","Cannot"]' \
  -p 'log_type=local' \
  -p 'time_pattern=--'
```

> The kadmind log usually has no timestamp format; pass `time_pattern=--` to skip time filtering.

#### 4.3 Collect Kerberos Health Check/Monitor Logs

```bash
# Collect Kerberos service check logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/kerberos' \
  -p 'log_file_name=check-krb-availability*' \
  -p 'keywords=["ERROR","FAIL","abnormal","not available","down"]' \
  -p 'log_type=local' \
  -p 'time_pattern=--'
```

```bash
# Collect Kerberos service monitor logs
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/kerberos' \
  -p 'log_file_name=krb_server_mon*' \
  -p 'keywords=["ERROR","FAIL","abnormal","down","not available"]' \
  -p 'log_type=local' \
  -p 'time_pattern=--'
```

```bash
# Collect OMS Kerberos service check logs (when the alarm role is okerberos)
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/okerberos' \
  -p 'log_file_name=checkservice_detail*' \
  -p 'keywords=["ERROR","FAIL","abnormal","not available","down"]' \
  -p 'log_type=local' \
  -p 'time_pattern=--'
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
| `<alarm_time>` | Alarm occurrence time | 2026/09/02 10:00:00 GMT+08:00 |
