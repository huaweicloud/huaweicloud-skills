# Instance Layer Diagnosis

> This file is loaded at SKILL.md Step 4. The instance layer is the core of the propagation chain — it judges upward whether the fault propagates to the service layer, and downward whether the root cause is at the host layer. If there is a 12007 alarm, go to Step 4 (reference 12007 diagnosis); if no alarm, go to Step 5 (scenario identification + status diagnosis) or Step 6 (runtime exception diagnosis).

## Diagnosis Flow

```
Step 1: Confirm instance status (alarm + status)
  │
  ├─ Has 12007 alarm → Step 4: Reference 12007 alarm diagnosis
  │
  ├─ No alarm but process/port abnormal → Step 5: Scenario identification + status diagnosis
  │    ├─ Scenario identified (install/start/stop etc.) → Load scenarios/<scenario>.md for scenario-specific checks
  │    └─ Cannot identify scenario → General instance diagnosis (process/log/permission/disk checks)
  │
  └─ No alarm and process/port normal but has ERROR → Step 6: Runtime exception diagnosis
```

## Step 1: Confirm Instance Status (Alarm + Status)

> Base data was collected in SKILL.md Step 1, use it directly here.

### 1.1 Determine Current Instance Status

Comprehensively use the data collected in SKILL.md Step 1:

| Process Status | Port Status | HA Status | Alarm | Next Step |
|----------------|-------------|-----------|-------|-----------|
| Does not exist | Not listening | Stopped/None | Has 12007 | Step 4 |
| Does not exist | Not listening | Stopped | No 12007 | Step 5 (scenario: stop succeeded) |
| Does not exist | Not listening | Failed/None | Yes/No | Step 5 (scenario identification) |
| Does not exist | Still listening | — | Yes/No | Step 5 (scenario: incomplete stop) |
| Exists | Not listening | — | Yes/No | Step 5 (scenario: start failure) |
| Exists | Listening | Non-Normal | Yes/No | Step 6 (HA abnormal) |
| Exists | Listening | Normal | Has 12007 | Step 4 |
| Exists | Listening | Normal | No | Step 6 (check logs for ERROR) |

### 1.2 Determine Whether Host is Faulty

Check host status (result from SKILL.md Step 2):

| Host Status | Conclusion | Propagation Path |
|-------------|------------|-----------------|
| Host BAD/unreachable | Root cause is host fault, instance abnormality is propagation result | Record propagation path: host fault → instance abnormal, jump to `host_fault.md` |
| Host normal | Instance independent fault | Continue to Step 4/5/6 |

---

## Step 4: Reference 12007 Alarm Diagnosis (When Alarm Exists)

> **Reference alarm diagnosis document**: Load the "alarm document reference" table in `components/<service_name>.md` to get the document path for the process fault alarm,
> follow the diagnosis flow in `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12007.md`.
>
> **Parameter Mapping**:
>
> | Variable in 12007 doc | Variable in this doc |
> |-----------------------|---------------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<service_name>` | `<service_name>` |
> | `<role_name>` | `<role_name>` |
> | `<node_name>` | `<node_name>` |
> | `<instance_name>` | Obtained from instance query results in SKILL.md Step 1 |

The 12007.md diagnosis flow already includes:
- Process status confirmation and batch alarm troubleshooting
- 12006 companion alarm check
- Directory permission troubleshooting
- Disk space troubleshooting
- Component process fault handling (Step 5 references `12007/<service_name>.md`)
- Health check interface/script troubleshooting

---

## Step 5: Scenario Identification + Status Diagnosis (When No Alarm or Alarm Missing)

> When there is no 12007 alarm, but process/port/HA status is abnormal, identify the operation scenario and execute diagnosis through this step.
> **Status first, logs supplementary**: First use current status to judge, then use framework logs to supplement, do not rely on component's own logs.

### 5.1 Pure Status Scenario Identification

First use process/port/HA status to directly determine:

| Process Status | Port Status | HA Status | Inferred Scenario | Confidence | Load File |
|----------------|-------------|-----------|-------------------|------------|-----------|
| Does not exist | Not listening | Stopped | stop (normal stop) | High | `scenarios/stop.md` |
| Does not exist | Not listening | Failed | stop failure or start failure | Medium | Needs log assistance |
| Does not exist | Not listening | No HA | Not installed or uninstalled | Low | Needs log assistance |
| Does not exist | Still listening | — | Incomplete stop | Medium | `scenarios/stop.md` |
| Exists | Not listening | — | start failure (initializing or failed) | Medium | Needs log assistance |
| Exists | Listening | Non-Normal | HA abnormal | Medium | General diagnosis |

### 5.2 Framework Log Assisted Identification

When pure status cannot determine the scenario, use the framework operation logs collected in SKILL.md Step 1.8 to assist:

> **Note**: Only use Controller exe.log and NodeAgent scriptlog (framework layer), do not use component's own logs (formats vary and are unreliable).

#### 5.2.1 Identify Operation Sequence

MRS operations have fixed sequences, multiple keywords appearing in logs simultaneously is normal:

| Log Operation Combination | Actual Operation | Last Operation in Sequence |
|---------------------------|-------------------|---------------------------|
| install → start | Install (includes auto-start) | start |
| uninstall → stop | Uninstall (includes stop) | uninstall |
| uninstall only (no stop) | Uninstall incomplete | uninstall |
| reinstall → restore → start | Reinstall | start |
| reinstall only (no restore/start) | Reinstall incomplete | reinstall |
| reinstall_host → install → start | Host reinstall (includes reinstall and start) | start |
| stop → start | Restart | start |
| stop only | Stop | stop |
| scale_out → install → start | Scale out | start |
| scale_in → stop → decommission | Scale in | decommission |
| install only (no start) | Install incomplete | install |

#### 5.2.2 Combined with Status to Locate Failure Position

| Operation Sequence | Process Status | Port Status | Inferred Scenario | Load File |
|-------------------|---------------|-------------|------------------|-----------|
| install→start | Does not exist | Not listening | start failure (install succeeded but start failed) | `scenarios/start.md` |
| install→start | Exists | Not listening | start failure (initialization incomplete) | `scenarios/start.md` |
| install→start | Exists | Listening | Success (check logs for ERROR) | Step 6 |
| install only | Does not exist | Not listening | install failure | `scenarios/install.md` |
| uninstall→stop | Does not exist | Not listening | uninstall success (uninstalled normally) | `scenarios/uninstall.md` |
| uninstall→stop | Exists | Still listening | uninstall failure (process residual) | `scenarios/uninstall.md` |
| uninstall only | Exists | Still listening | uninstall failure (uninstalled without stopping) | `scenarios/uninstall.md` |
| stop→start | Does not exist | Not listening | start failure (restart start failed) | `scenarios/start.md` |
| stop→start | Does not exist | Still listening | Incomplete stop | `scenarios/stop.md` |
| stop only | Does not exist | Not listening | stop success | `scenarios/stop.md` |
| stop only | Exists | Still listening | stop failure | `scenarios/stop.md` |
| reinstall→start | Does not exist | Not listening | start failure (start failed after reinstall) | `scenarios/reinstall.md` |
| reinstall only | Does not exist | Not listening | reinstall failure | `scenarios/reinstall.md` |
| scale_out→install | Does not exist | Not listening | scale_out failure | `scenarios/scale_out.md` |
| scale_in→stop | Exists | Still listening | scale_in failure | `scenarios/scale_in.md` |

#### 5.2.3 Time Sorting to Locate Last Operation (When Logs Are Large)

When there are many operation records in the log, find the record with the latest timestamp to determine current position:

1. Take the last non-ERROR record → "Last executed operation"
2. Take the last ERROR/fail record → "Last failed operation"
3. Combine both to determine the failure position

#### 5.2.4 Common Combination Quick Judgment

| Framework Log Contains | And Process Does Not Exist | And Port Not Listening | Quick Inference |
|------------------------|---------------------------|------------------------|-----------------|
| install + start + fail | Yes | Yes | start failure |
| install + fail (no start) | Yes | Yes | install failure |
| reinstall + restore + fail | Yes | Yes | reinstall failure |
| stop + success (no start) | Yes | Yes | stop success |
| stop + start + fail | Yes | Yes | start failure (restart) |
| stop + fail | No (process still exists) | Yes | stop failure |
| No operation logs at all | Yes | Yes | Alarm-driven instance fault (fallback) |

### 5.3 Pure Status Fallback When No Logs

When framework logs are also empty (API returns `[]`), rely entirely on status to infer:

| Current Status | Default Inference | Confidence | Handling |
|----------------|-------------------|------------|----------|
| Process does not exist + port not listening + HA Stopped | stop | Medium | Load `scenarios/stop.md` |
| Process does not exist + port not listening + No HA | Not installed or uninstalled | Low | General instance diagnosis |
| Process does not exist + port not listening + HA Failed | Stop/start failure | Low | General instance diagnosis |
| Process does not exist + port not listening + HA normal but Active | Possibly wrong node queried | Medium | Check peer node |
| Process exists + port not listening | start failure | Medium | General instance diagnosis |

> **Key Principle**: When pure status cannot distinguish install/reinstall/start/stop, use general instance diagnosis (Step 5.4), covering various situations of process absence. When confidence is low, note in conclusion: "Suggest user provide operation type or operation time for precise location."

### 5.4 General Instance Diagnosis (When Scenario Cannot Be Identified)

When the specific scenario cannot be determined, execute the following general checks:

#### 5.4.1 Process Missing Cause Troubleshooting

```bash
# Check NodeAgent script logs for process-related errors
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","exit","OOM","kill","signal","permission","denied"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Common root causes:

| Log Keywords | Possible Cause | Repair Suggestion |
|--------------|----------------|-------------------|
| OOM / OutOfMemory | Process killed due to insufficient memory | Expand memory or adjust JVM parameters |
| Permission denied | Insufficient permissions | Check file/directory permissions |
| Port already in use | Port conflict | Stop old process occupying the port |
| No such file or directory | File missing | Check installation directory integrity |
| Segmentation fault / core dump | Process crash | Check core dump file |
| No ERROR logs | Possibly normal stop or manually killed | Check framework logs to confirm operation |

#### 5.4.2 Disk Space Troubleshooting

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

#### 5.4.3 Directory Permission Troubleshooting

```bash
# Check script logs for permission-related errors
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","permission","chmod","chown","owner","denied","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 5.5 After Scenario Is Identified

If Steps 5.1-5.3 identified a specific scenario, load `scenarios/common.md` to execute the general 6-phase check, then load `scenarios/<scenario>.md` to execute scenario-specific checks.

The check steps in scenario files reference information in component configuration files (ports, log paths, data directories, etc.), different components automatically use different check parameters under the same scenario.

---

## Step 6: Runtime Exception Diagnosis (Process/Port Normal but Abnormal)

> Process exists, port listening, HA normal, but user reported issues, or logs contain ERROR.

### 6.1 Check Component Logs for ERROR

Based on the `log path` table in the component configuration file, execute checks for each role's log directory:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception","FATAL","fail","timeout","OOM","OutOfMemory","crash"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 6.2 Check HA Status

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 6.3 Judgment

| Check Result | Inference | Next Step |
|--------------|-----------|-----------|
| Logs have ERROR/Exception | Instance runtime abnormal | Analyze ERROR type, provide repair suggestions |
| HA resource status non-Normal | HA abnormal | Check HA logs, suggest active/standby switchover |
| Disk usage ≥85% | Insufficient resources | Alarm-driven host fault |
| Everything normal | Component running normally | Output normal conclusion |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------------|-----------------|-------------------|---------------------|
| Process OOM Killed | Logs have OOM/OutOfMemory | Expand memory or adjust JVM parameters | — |
| Port conflict | Process exists but port not listening, logs have port in use | Stop old process occupying the port | `scenarios/start.md` |
| Configuration file missing | Script logs have config not found / missing | Regenerate configuration file | `scenarios/install.md` |
| Permission issue | Script logs have Permission denied | Check file/directory permissions | — |
| Dependency service not ready | Component logs have connection refused/timeout | Start dependency service first | Component config file `dependency` table |
| Disk full | disk-space check shows ≥100% | Clean up disk space | — |
| Process crash | Logs have Segmentation fault/core dump | Check core dump file | — |
| Install failure | Framework logs have install fail | Check installation package and config generation | `scenarios/install.md` |
| Stop failure | Process still exists, framework logs have stop fail | Check process status (D-state/Z-state) | `scenarios/stop.md` |

## Variable Description

| Variable | Description | Example |
|----------|-------------|---------|
| `<cluster_id>` | MRS cluster identifier | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<node_name>` | Faulty host name | 8-5-225-6 |
| `<service_name>` | Service name | KrbServer |
| `<role_name>` | Role name | KerberosServer |
| `<instance_name>` | Instance name | 1_8_NameNode |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<process_name>` | Component configuration file | krb5kdc, gaussdb |
| `<port_number>` | Component configuration file | 21732, 20013 |
| `<log_directory>` | Component configuration file | /var/log/Bigdata/kerberos/ |
| `<log_file_name>` | Component configuration file | krb5kdc.log* |
