# Uninstall Scenario Diagnosis

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Uninstall Status Check — Process running, HA role, dependency relationship
  │
  ├─ Step 2: Uninstall Execution Check — Uninstall errors in Controller/NodeAgent logs
  │
  ├─ Step 3: Residual Check — Process residual, port residual, file residual
  │
  └─ Step 4: Post-Uninstall Verification — Process gone, port released, directory cleaned
```

## Step 1: Pre-Uninstall Status Check

**Goal**: Confirm the component's running status before the uninstall operation, and determine whether there are factors blocking the uninstall

### 1.1 Process Status Check

Based on the `process name` in the component config file, confirm whether the component is running before uninstall:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file.

### 1.2 HA Role Status Check (HA components only)

HA must be stopped before uninstalling an HA component; check the HA resource status:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

### 1.3 Active Connection Check

Check whether the component currently has active connections, which may block the uninstall operation:

```bash
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Based on the `port` table in the component config file, execute this check for each port.

**Pre-Uninstall status assessment**:

| Status Item | Normal | Risk | Suggestion |
|-------------|--------|------|-----------|
| Process status | Stopped | Still running | Execute the stop operation first, then uninstall |
| HA role | HA stopped | Still Active/Standby | Stop HA (ha_monitor, ha.bin) first, then uninstall |
| Active connections | None or few | Many persistent connections | Investigate the connection sources, wait for release or force-disconnect |

---

## Step 2: Uninstall Execution Check

**Goal**: Confirm whether the uninstall command was correctly passed from Controller to NodeAgent and executed

### 2.1 Controller Uninstall Operation Log

Check the Controller logs for uninstall operation related errors:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common ERROR keywords**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Failed to send uninstall command | Command not delivered to NodeAgent | Check NodeAgent status and network |
| Uninstall timeout | Uninstall operation timed out | Process refuses to exit or files are occupied |
| Agent timeout | Agent response timeout | NodeAgent abnormal or under high load |
| Operation rejected | Operation rejected | Current state does not allow uninstall (e.g., component still running) |
| Dependency exists | Other services depend on this component | Uninstall or stop the dependent service first |

### 2.2 NodeAgent Uninstall Execution Log

Check the NodeAgent logs for uninstall operation execution:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 2.3 NodeAgent Uninstall Script Execution Log

Check the uninstall script execution:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Result mapping**:

| Controller Log | NodeAgent Log | Script Log | Conclusion |
|----------------|---------------|------------|------------|
| Has ERROR | — | — | Controller layer uninstall command send failed |
| Normal | Has ERROR | — | NodeAgent layer uninstall execution abnormal |
| Normal | Normal | Has ERROR | Uninstall script execution failed, go to Step 3 to investigate |
| Normal | Normal | Normal | Uninstall command executed, go to Steps 3-4 for verification |

---

## Step 3: Residual Check

**Goal**: Confirm no process, port, or file residual after uninstall

### 3.1 Residual Process Check

Check whether the target node still has residual component processes (the process should not exist after uninstall):

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file. If the process still exists, the uninstall operation was not fully executed.

### 3.2 Residual Port Check

Check whether the component port is still occupied (the port should be released after uninstall):

```bash
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

### 3.3 Child Process Residual Check

Check whether there are child processes that were not cleaned up (the parent process was uninstalled but the child processes are still running):

```bash
# manager mode uses get_host_process instead of omm-process-tree
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Check whether the process tree has residual child processes whose parent node is a process related to `<service_name>`.

### 3.4 Cleanup Execution Log Check

Check the NodeAgent script logs for cleanup operation related records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
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

**Goal**: Confirm that the component has been fully uninstalled, with no residual processes or port occupation

### 4.1 Process Disappearance Verification

Based on the `process name` in the component config file, confirm that all related processes no longer exist:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

The expected result is that the process does not exist.

### 4.2 Port Release Verification

Based on the `port` table in the component config file, confirm that all ports have been released:

```bash
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

The expected result is that the port is not being listened on.

### 4.3 Residual File Check

Check for residual installation directories, configuration files, lock files, or PID files:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 4.4 HA Status Verification (HA components only)

Confirm whether the HA resource status is as expected after uninstall:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

### 4.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Uninstall` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `get_host_process`
- Log check → `browse_log` / `start_log_search`
- HA status → `get_instances`

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Uninstall without stopping the component | Process still exists, logs have Operation rejected | Execute the stop operation first, then uninstall |
| Uninstall without stopping HA | HA resource not released, uninstall logs have HA conflict | Stop HA (ha_monitor, ha.bin) first, then uninstall |
| Process hung and refuses to exit | Process state is D or Z, kill signal ineffective | D state: investigate the I/O issue or restart the node; Z state: find the parent process to reclaim |
| Files occupied | Script logs have Permission denied or device busy | Check the process occupying the file, release it, then retry |
| Dependent service not uninstalled | Controller logs have Dependency exists | Uninstall the other services that depend on this component first, in dependency order |
| Cleanup script failed | Script logs have ERROR/fail | Check the cleanup script logic and permissions |
| Insufficient disk space | disk-space check shows ≥85% | Clean up disk space, then retry uninstall |
| Child process residual | Parent process uninstalled but child processes remain | Check whether the uninstall script handles child processes, manually kill residual child processes |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Uninstall target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | Process name of each component role |
| <port> | Component config file | Port of each component role |
