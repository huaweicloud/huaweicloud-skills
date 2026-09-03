# Uninstall Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Uninstall Status Check — Process running, HA role, dependencies
  │
  ├─ Step 2: Uninstall Execution Check — Uninstall errors in Controller/NodeAgent logs
  │
  ├─ Step 3: Residual Check — Process residuals, port residuals, file residuals
  │
  └─ Step 4: Post-Uninstall Verification — Process disappeared, port released, directory cleaned
```

## Step 1: Pre-Uninstall Status Check

**Goal**: Confirm the component's running status before the uninstall operation is executed, determining whether there are factors preventing uninstall

### 1.1 Process Status Check

Based on the `process name` in the component config file, confirm whether the component is running before uninstall:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file.

### 1.2 HA Role Status Check (HA components only)

HA must be stopped before uninstalling HA components; check HA resource status:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 1.3 Active Connection Check

Check whether the component currently has active connections; active connections may cause the uninstall operation to block:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Based on the `port` table in the component config file, execute this check for each port.

**Pre-Uninstall Status Assessment**:

| Status Item | Normal | Risk | Suggestion |
|-------------|--------|------|------------|
| Process status | Stopped | Still running | Execute stop operation before uninstall |
| HA role | HA stopped | Still Active/Standby | Stop HA (ha_monitor, ha.bin) before uninstall |
| Active connections | None or few | Large number of persistent connections | Investigate connection source, wait for release or force disconnect |

---

## Step 2: Uninstall Execution Check

**Goal**: Confirm whether the uninstall command was correctly transmitted from Controller to NodeAgent and executed

### 2.1 Controller Uninstall Operation Logs

Check the Controller logs for uninstall operation related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","uninstall","remove","delete","ERROR","failed","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common ERROR Keywords**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Failed to send uninstall command | Command not delivered to NodeAgent | Check NodeAgent status and network |
| Uninstall timeout | Uninstall operation timed out | Process refuses to exit or files are occupied |
| Agent timeout | Agent response timed out | NodeAgent abnormal or under high load |
| Operation rejected | Operation rejected | Current state does not allow uninstall (e.g., component still running) |
| Dependency exists | Other services depend on this component | Uninstall or stop dependency services first |

### 2.2 NodeAgent Uninstall Execution Logs

Check the NodeAgent logs for uninstall operation execution:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","uninstall","ProcessAction","remove","delete","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 2.3 NodeAgent Uninstall Script Execution Logs

Check the uninstall script execution:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","uninstall","remove","delete","clean","rm","ERROR","fail","exit","refused"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer uninstall command dispatch failed |
| Normal | Has ERROR | — | NodeAgent layer uninstall execution abnormal |
| Normal | Normal | Has ERROR | Uninstall script execution failed, proceed to Step 3 |
| Normal | Normal | Normal | Uninstall command executed, proceed to Steps 3-4 for verification |

---

## Step 3: Residual Check

**Goal**: Confirm no process, port, or file residuals after uninstall

### 3.1 Residual Process Check

Check whether the target node still has residual component processes (processes should not exist after uninstall):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file. If the process still exists, the uninstall operation was not fully executed.

### 3.2 Residual Port Check

Check whether the component port is still occupied (port should be released after uninstall):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

### 3.3 Child Process Residual Check

Check whether there are child processes that were not cleaned up (parent process uninstalled but child processes still running):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

Check whether there are residual child processes in the process tree with `<service_name>`-related processes as parent nodes.

### 3.4 Cleanup Execution Log Check

Check the NodeAgent script logs for cleanup operation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","clean","cleanup","remove","delete","uninstall","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Process still exists | Uninstall operation incomplete or process zombie | Manually kill residual processes and retry |
| Port still occupied | Process not fully exited | Confirm process has stopped, wait for port release |
| HA resource not released | HA not stopped before uninstall | Stop HA (ha_monitor, ha.bin) first, then uninstall |
| Cleanup script failed | Files occupied or insufficient permissions | Check file occupation and permissions |
| Data directory residual | Cleanup script not executed or skipped | Manually confirm data directory status |

---

## Step 4: Post-Uninstall Verification

**Goal**: Confirm that the component has been completely uninstalled, with no residual processes or port occupation

### 4.1 Process Disappearance Verification

Based on the `process name` in the component config file, confirm that all related processes no longer exist:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Expected result: process does not exist.

### 4.2 Port Release Verification

Based on the `port` table in the component config file, confirm that all ports have been released:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Expected result: port is not being listened on.

### 4.3 Residual File Check

Check whether there are residual installation directories, configuration files, lock files, or PID files:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","uninstall","cleanup","remove","rm","residual","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 4.4 HA Status Verification (HA components only)

Confirm that the HA resource status after uninstall meets expectations:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 4.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Uninstall` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Component not stopped before uninstall | Process still exists, logs have Operation rejected | Execute stop operation before uninstall |
| HA not stopped before uninstall | HA resource not released, uninstall logs have HA conflict | Stop HA (ha_monitor, ha.bin) before uninstall |
| Process stuck refusing to exit | Process status is D or Z, kill signal ineffective | D-state requires investigating I/O issues or rebooting node; Z-state requires finding parent process to reap |
| Files occupied | Script logs have Permission denied or device busy | Check file-occupying processes, release and retry |
| Dependency service not uninstalled | Controller logs have Dependency exists | Uninstall services that depend on this component first, in dependency order |
| Cleanup script failed | Script logs have ERROR/fail | Check cleanup script logic and permissions |
| Insufficient disk space | disk-space check shows ≥85% | Clean up disk space, then retry uninstall |
| Child process residual | Parent process uninstalled but child processes remain | Check whether uninstall script handles child processes, manually kill residual child processes |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Uninstall target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | Process names for each role of the component |
| <port_number> | Component config file | Ports for each role of the component |
