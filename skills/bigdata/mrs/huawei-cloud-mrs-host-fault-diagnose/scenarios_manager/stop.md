# Stop Scenario Diagnosis (stop)

> Prerequisites: The common check phases 1-5 of common.md have been completed
> Component config: load `components/<service_name>.md` to obtain component information

## Diagnosis Flow

```
Step 1: Pre-Stop State Check — Active connections, running tasks, HA role
  │
  ├─ Step 2: Stop Execution Check — Stop errors in Controller/NodeAgent logs
  │
  ├─ Step 3: Process Exit Check — Whether the process was killed, zombie processes, refusal to stop
  │
  └─ Step 4: Post-Stop Verification — Process gone, port released, no residuals
```

## Step 1: Pre-Stop State Check

**Goal**: Confirm the component's running state before the stop operation is executed, and identify any factors that may prevent stopping

### 1.1 Active Connection Check

Check whether the component currently has active connections; active connections may block the stop operation:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Based on the `port` table in the component config file, execute this check for each port to determine whether any external connection is holding the port continuously.

### 1.2 Running Task Check

Check the component logs for long-running tasks currently in progress (such as large queries, data writes):

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=running' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

### 1.3 HA Role Status Check (HA components only)

Check the current Active/Standby role of the HA component; stopping the Active node may trigger a primary/standby failover:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**Pre-Stop State Assessment**:

| State Item | Normal | Risk | Suggestion |
|------------|--------|------|------------|
| Active connections | None or few | Many persistent connections | Investigate the connection source; wait for release or force disconnect |
| Running tasks | No long tasks | Long-running tasks present | Wait for the tasks to complete before stopping |
| HA role | Stop the Standby node | Stop the Active node | Perform a primary/standby failover first, then stop the original Active node |

---

## Step 2: Stop Execution Check

**Goal**: Confirm whether the stop command was correctly transmitted from Controller to NodeAgent and executed

### 2.1 Controller Stop Operation Logs

Check the Controller logs for errors related to the stop operation:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common ERROR Keywords**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|---------------|-------------------|
| Failed to send stop command | Command not delivered to NodeAgent | Check the NodeAgent state and network |
| Stop timeout | Stop operation timed out | Process refuses to stop or is stuck; proceed to Step 3 to investigate |
| Agent timeout | Agent response timed out | NodeAgent abnormal or under high load |
| Operation rejected | Operation rejected | Current state does not allow stop (e.g. another operation in progress) |

### 2.2 NodeAgent Stop Execution Logs

Check the NodeAgent logs for the stop operation execution:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 2.3 NodeAgent Stop Script Execution Logs

Check the stop script execution:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer stop command dispatch failed |
| Normal | Has ERROR | — | NodeAgent layer stop execution abnormal |
| Normal | Normal | Has ERROR | Stop script execution failed; proceed to Step 3 to investigate |
| Normal | Normal | Normal | Stop command executed; proceed to Steps 3-4 to verify |

---

## Step 3: Process Exit Check

**Goal**: Confirm whether the process has exited correctly, and identify zombie processes, D-state processes, or processes refusing to stop

### 3.1 Process State Check

Based on the `process name` in the component config file, check whether the process still exists and its state:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file.

**Process State Analysis**:

| Process State | Meaning | Conclusion | Handling Suggestion |
|---------------|---------|------------|----------------------|
| Process does not exist | Exited normally | Stop succeeded | Proceed to Step 4 to verify |
| R (Running) | Still running | Process did not respond to the stop signal | Check whether the kill signal was delivered |
| D (Uninterruptible sleep) | Waiting for I/O | Process stuck in kernel-mode I/O | Wait for I/O to complete or restart the node |
| Z (Zombie) | Zombie process | Child process exited but not reaped | Find the parent process and handle it |
| T (Stopped) | Suspended | Process suspended but not exited | Send SIGKILL to force termination |

### 3.2 Zombie Process and D-State Process Check

Check whether there are zombie processes (Z state) or D-state (uninterruptible sleep) processes:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file, and analyze the running state (R/D/Z/T) of the processes in the returned result.

> **Note**: D-state processes are usually stuck in I/O operations (such as disk read/write, NFS waits).
> In this case an ordinary kill -9 cannot terminate them; the underlying I/O problem needs to be investigated or the node restarted.

### 3.3 Residual Child Process Check

Check whether there are child processes that were not stopped (parent process exited but child processes still running):

```bash
# In manager mode, use get_host_process instead of omm-process-tree
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Check whether the process tree contains residual child processes whose parent node is a `<service_name>`-related process.

### 3.4 Kill Signal Delivery Check

Check the NodeAgent logs for kill signal sending records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

---

## Step 4: Post-Stop Verification

**Goal**: Confirm that the component has been fully stopped, with no residual processes or port occupation

### 4.1 Process Disappearance Verification

Based on the `process name` in the component config file, confirm that all related processes no longer exist:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file; the expected result is that the process does not exist.

### 4.2 Port Release Verification

Based on the `port` table in the component config file, confirm that all ports have been released:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

The expected result is that the ports are not listening.

### 4.3 Residual Resource Check

Check whether any residual lock files, PID files, or temporary files remain:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 4.4 HA Status Verification (HA components only)

Confirm that the HA resource status after stop meets expectations:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**Post-Stop Verification Results**:

| Check Item | Expected Result | Abnormal Result | Conclusion |
|------------|----------------|-----------------|------------|
| Process | Does not exist | Still exists | Stop failed; return to Step 3 to investigate |
| Port | Not listening | Still listening | Process did not exit completely or there are residuals |
| Residual files | Cleared | PID/lock files present | Stop script did not complete cleanup |
| HA status | Resource migrated/stopped | Resource abnormal | HA primary/standby failover abnormal |

### 4.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Stop (stop)` section of the component config file,
load the component config and execute each check item.

For each check item, choose the appropriate API call based on the check content it describes:
- Process/port check → `get_host_process`
- Log check → `browse_log` / `start_log_search`
- HA status → `get_instances`

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristic | Repair Suggestion |
|------------|---------------|-------------------|
| Process stuck (zombie/D state) | Process state is Z or D, kill signal ineffective | For D state, investigate the I/O problem or restart the node; for Z state, find the parent process to reap |
| Kill signal not delivered | NodeAgent log has no SIGTERM/SIGKILL record | Check the communication between NodeAgent and the process; manually send the kill signal |
| Child process not stopped | Parent process exited but child processes remain | Check whether the stop script handles child processes; manually kill residual child processes |
| HA primary/standby failover triggered | Stopping the Active node caused automatic failover | Manually failover to the Standby node first, then stop the original Active node |
| Long-running task blocks stop | Component log has a query/transaction in progress | Wait for the task to complete or terminate the task, then stop |
| Stop script execution failed | Script log has ERROR/fail | Check the stop script logic and permissions |
| Active connections holding the port | Port check shows connections still present | Investigate the connection source, disconnect, then stop again |
| I/O wait causes D-state process | Process stuck in disk/NFS I/O | Investigate storage faults; restart the node if necessary |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Stop target node |
| <oms_active_node> | common.md Phase 1 | OMS primary node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | Process name of each component role |
| <port> | Component config file | Port of each component role |
| <log_directory> | Component config file | Log path of each component role |
| <log_file_name> | Component config file | Log file name of each component role |
