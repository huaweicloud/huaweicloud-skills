# Instance Layer Diagnosis

> This file is loaded in step 3 of SKILL.md. The instance layer is the core of the propagation chain -- determine upward whether it propagates to the service layer, and downward whether the root cause is at the host layer.
> If there is a 12007 alarm, go to step 4 (reference 12007 diagnosis); if no alarm, go to step 5 (scenario recognition + status diagnosis) or step 6 (runtime abnormality diagnosis).

## Diagnosis Flow

```
Step 1: Confirm instance status (alarm + status)
  │
  ├─ Has 12007 alarm → Step 4: Reference 12007 alarm diagnosis
  │
  ├─ No alarm but process/port abnormal → Step 5: Scenario recognition + status diagnosis
  │    ├─ Scenario recognized (install/start/stop etc.) → Load scenarios_manager/<scenario>.md to execute scenario-specific checks
  │    └─ Scenario cannot be recognized → Generic instance diagnosis (process/log/permission/disk checks)
  │
  └─ No alarm, process and port normal but has ERROR → Step 6: Runtime abnormality diagnosis
```

## Step 1: Confirm Instance Status (alarm + status)

> Basic data has already been collected in step 1 of SKILL.md and is used directly here.

### 1.1 Determine Current Instance Status

Consolidate the data collected in step 1 of SKILL.md:

| Process Status | Port Status | HA Status | Alarm | Next Step |
|---------|---------|--------|------|--------|
| Not present | Not listening | Stopped/none | Has 12007 | Step 4 |
| Not present | Not listening | Stopped | No 12007 | Step 5 (scenario: stop succeeded) |
| Not present | Not listening | Failed/none | Has/no | Step 5 (scenario recognition) |
| Not present | Still listening | — | Has/no | Step 5 (scenario: stop incomplete) |
| Present | Not listening | — | Has/no | Step 5 (scenario: start failed) |
| Present | Listening | Non-Normal | Has/no | Step 6 (HA abnormal) |
| Present | Listening | Normal | Has 12007 | Step 4 |
| Present | Listening | Normal | No | Step 6 (check log ERROR) |

### 1.2 Determine Whether the Host Has Failed

Check the host status (result of step 2 in SKILL.md):

| Host Status | Conclusion | Propagation Path |
|---------|------|---------|
| Host BAD/unreachable | Root cause is host fault; instance abnormality is the propagated result | Record propagation path: host fault → instance abnormality, jump to `host_fault.md` |
| Host normal | Instance fails independently | Continue to step 4/5/6 |

---

## Step 4: Reference 12007 Alarm Diagnosis (when there is an alarm)

> **Reference alarm diagnosis document**: Load the "alarm document reference" table in `components/<service_name>.md` to obtain the document path for the process-fault alarm,
> and execute according to the diagnosis flow in `../huawei-cloud-mrs-host-alarm-diagnose/alarm_manager/12007.md`.
>
> **Parameter mapping**:
>
> | Variable in 12007 doc | Variable in this document |
> |------------------|---------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<service_name>` | `<service_name>` |
> | `<role_name>` | `<role_name>` |
> | `<node_name>` | `<node_name>` |
> | `<instance_name>` | Obtained from the instance query result in step 1 of SKILL.md |

The diagnosis flow in 12007.md already includes:
- Process status confirmation and batch alarm troubleshooting
- 12006 accompanying alarm check
- Directory permission troubleshooting
- Disk space troubleshooting
- Component process fault handling (step 5 references `12007/<service_name>.md`)
- Health check interface/script troubleshooting

---

## Step 5: Scenario Recognition + Status Diagnosis (no alarm or missing alarm)

> When there is no 12007 alarm but process/port/HA status is abnormal, use this step to recognize the operation scenario and execute diagnosis.
> **Status primary, logs secondary**: first judge using current status, then use framework logs for assistance, without relying on the component's own logs.

### 5.1 Pure Status Scenario Recognition

First use process/port/HA status to judge directly:

| Process Status | Port Status | HA Status | Inferred Scenario | Confidence | File to Load |
|---------|---------|--------|---------|--------|---------|
| Not present | Not listening | Stopped | stop (normal stop) | High | `scenarios_manager/stop.md` |
| Not present | Not listening | Failed | stop failed or start failed | Medium | Requires log assistance |
| Not present | Not listening | No HA | Not installed or uninstalled | Low | Requires log assistance |
| Not present | Still listening | — | stop incomplete | Medium | `scenarios_manager/stop.md` |
| Present | Not listening | — | start failed (initializing or failed) | Medium | Requires log assistance |
| Present | Listening | Non-Normal | HA abnormal | Medium | Generic diagnosis |

### 5.2 Framework Log Assisted Recognition

When pure status cannot determine the scenario, use the framework operation logs collected in step 1.8 of SKILL.md as assistance:

> **Note**: Only use the Controller exe.log and NodeAgent scriptlog (framework layer), not the component's own logs (their formats vary and are unreliable).

#### 5.2.1 Recognize Operation Sequence

MRS operations follow a fixed sequence; multiple keywords appearing together in the logs is the norm:

| Log Operation Combination | Actual Operation | Last Operation in Sequence |
|-------------|---------|----------------|
| install → start | Install (including auto-start) | start |
| uninstall → stop | Uninstall (including stop) | uninstall |
| uninstall only (no stop) | Uninstall incomplete | uninstall |
| reinstall → restore → start | Reinstall | start |
| reinstall only (no restore/start) | Reinstall incomplete | reinstall |
| reinstall_host → install → start | Host reinstall (including reinstall and start) | start |
| stop → start | Restart | start |
| stop only | Stop | stop |
| scale_out → install → start | Scale out | start |
| scale_in → stop → decommission | Scale in | decommission |
| install only (no start) | Install incomplete | install |

#### 5.2.2 Combine Status to Locate the Failure Position

| Operation Sequence | Process Status | Port Status | Inferred Scenario | File to Load |
|---------|---------|---------|---------|---------|
| install→start | Not present | Not listening | start failed (install succeeded but start failed) | `scenarios_manager/start.md` |
| install→start | Present | Not listening | start failed (initialization incomplete) | `scenarios_manager/start.md` |
| install→start | Present | Listening | Succeeded (check log ERROR) | Step 6 |
| install only | Not present | Not listening | install failed | `scenarios_manager/install.md` |
| uninstall→stop | Not present | Not listening | uninstall succeeded (uninstall normal) | `scenarios_manager/uninstall.md` |
| uninstall→stop | Present | Still listening | uninstall failed (process residue) | `scenarios_manager/uninstall.md` |
| uninstall only | Present | Still listening | uninstall failed (uninstalled without stopping) | `scenarios_manager/uninstall.md` |
| stop→start | Not present | Not listening | start failed (start failed during restart) | `scenarios_manager/start.md` |
| stop→start | Not present | Still listening | stop incomplete | `scenarios_manager/stop.md` |
| stop only | Not present | Not listening | stop succeeded | `scenarios_manager/stop.md` |
| stop only | Present | Still listening | stop failed | `scenarios_manager/stop.md` |
| reinstall→start | Not present | Not listening | start failed (start failed after reinstall) | `scenarios_manager/reinstall.md` |
| reinstall only | Not present | Not listening | reinstall failed | `scenarios_manager/reinstall.md` |
| scale_out→install | Not present | Not listening | scale_out failed | `scenarios_manager/scale_out.md` |
| scale_in→stop | Present | Still listening | scale_in failed | `scenarios_manager/scale_in.md` |

#### 5.2.3 Sort by Time to Locate the Last Operation (when logs are large)

When there are many operation records in the logs, find the record with the latest timestamp to determine the current position:

1. Take the last non-ERROR record → "last executed operation"
2. Take the last ERROR/fail record → "last failed operation"
3. Combine the two to determine the failure position

#### 5.2.4 Quick Judgment of Common Combinations

| Framework Log Contains | And Process Not Present | And Port Not Listening | Quick Inference |
|-------------|------------|------------|---------|
| install + start + fail | Yes | Yes | start failed |
| install + fail (no start) | Yes | Yes | install failed |
| reinstall + restore + fail | Yes | Yes | reinstall failed |
| stop + success (no start) | Yes | Yes | stop succeeded |
| stop + start + fail | Yes | Yes | start failed (restart) |
| stop + fail | No (process still present) | Yes | stop failed |
| No operation log at all | Yes | Yes | Alarm-driven - instance fault (fallback) |

### 5.3 Pure Status Fallback When No Logs

When the framework logs are also empty (API returns `[]`), rely entirely on status inference:

| Current Status | Default Inference | Confidence | Handling |
|---------|---------|--------|------|
| Process not present + port not listening + HA Stopped | stop | Medium | Load `scenarios_manager/stop.md` |
| Process not present + port not listening + no HA | Not installed or uninstalled | Low | Generic instance diagnosis |
| Process not present + port not listening + HA Failed | Stop/start failed | Low | Generic instance diagnosis |
| Process not present + port not listening + HA normal but Active | Possibly checking the wrong node | Medium | Check the peer node |
| Process present + port not listening | start failed | Medium | Generic instance diagnosis |

> **Key principle**: When pure status cannot distinguish install/reinstall/start/stop, use the generic instance diagnosis (step 5.4), which covers the various cases of missing processes. When confidence is low, note in the conclusion "suggest the user provide the operation type or operation time for precise location."

### 5.4 Generic Instance Diagnosis (when the scenario cannot be recognized)

When the specific scenario cannot be determined, execute the following generic checks:

#### 5.4.1 Troubleshoot the Cause of a Missing Process

```bash
# Check process-related errors in the NodeAgent script log
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Common root causes:

| Log Keyword | Possible Cause | Repair Suggestion |
|------------|---------|---------|
| OOM / OutOfMemory | Process killed due to insufficient memory | Expand memory or adjust JVM parameters |
| Permission denied | Insufficient permission | Check file/directory permissions |
| Port already in use | Port conflict | Stop the old process occupying the port |
| No such file or directory | Missing file | Check the installation directory integrity |
| Segmentation fault / core dump | Process crashed | Check the core dump file |
| No ERROR log | Possibly stopped normally or killed manually | Check the framework logs to confirm the operation |

#### 5.4.2 Disk Space Troubleshooting

```bash
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

#### 5.4.3 Directory Permission Troubleshooting

```bash
# Check permission-related errors in the script log
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=permission' --json
```

### 5.5 After the Scenario Is Recognized

If a specific scenario is recognized in steps 5.1-5.3, load `scenarios_manager/common.md` to execute the generic 6-phase check, then load `scenarios_manager/<scenario>.md` to execute scenario-specific checks.

The check steps in the scenario file reference information from the component config file (port, log path, data directory, etc.); different components will automatically use different check parameters for the same scenario.

---

## Step 6: Runtime Abnormality Diagnosis (process and port normal but abnormal)

> Process present, port listening, HA normal, but the user has reported a problem or there is ERROR in the logs.

### 6.1 Check ERROR in Component Logs

According to the `log path` table in the component config file, execute checks on the log directory of each role:

```bash
# Use start_log_search to query ERROR keywords in component logs
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service_name>:<role_name>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=ERROR' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

# Query the log search progress
python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

### 6.2 Check HA Status

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

### 6.3 Determine

| Check Result | Inference | Next Step |
|---------|------|--------|
| Log has ERROR/Exception | Instance runtime abnormal | Analyze the ERROR type and provide a repair suggestion |
| HA resource status is Non-Normal | HA abnormal | Check the HA logs, suggest active/standby switchover |
| Disk usage ≥85% | Insufficient resources | Alarm-driven - host fault |
| Everything normal | Component running normally | Output a normal conclusion |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------|------|----------|----------|
| Process OOM Kill | Log has OOM/OutOfMemory | Expand memory or adjust JVM parameters | — |
| Port conflict | Process present but port not listening, log has port in use | Stop the old process occupying the port | `scenarios_manager/start.md` |
| Missing config file | Script log has config not found / missing | Regenerate the config file | `scenarios_manager/install.md` |
| Permission issue | Script log has Permission denied | Check file/directory permissions | — |
| Dependent service not ready | Component log has connection refused/timeout | Start the dependent service first | `dependency` table in the component config file |
| Disk full | disk-space check shows ≥100% | Clean up disk space | — |
| Process crash | Log has Segmentation fault/core dump | Check the core dump file | — |
| Install failed | Framework log has install fail | Check the installation package and config generation | `scenarios_manager/install.md` |
| Stop failed | Process still present, framework log has stop fail | Check process status (D-state/Z-state) | `scenarios_manager/stop.md` |

## Variable Description

| Variable | Description | Example |
|------|------|------|
| `<cluster_id>` | MRS cluster ID | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<node_name>` | Fault host name | 8-5-225-6 |
| `<service_name>` | Service name | KrbServer |
| `<role_name>` | Role name | KerberosServer |
| `<instance_name>` | Instance name | 1_8_NameNode |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<process_name>` | From the component config file | krb5kdc, gaussdb |
| `<port_number>` | From the component config file | 21732, 20013 |
| `<log_directory>` | From the component config file | /var/log/Bigdata/kerberos/ |
| `<log_file_name>` | From the component config file | krb5kdc.log* |
