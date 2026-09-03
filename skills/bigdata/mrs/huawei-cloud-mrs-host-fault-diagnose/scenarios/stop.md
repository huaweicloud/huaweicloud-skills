# Stop Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Stop Status Check — Active connections, running tasks, HA role
  │
  ├─ Step 2: Stop Execution Check — Stop errors in Controller/NodeAgent logs
  │
  ├─ Step 3: Process Exit Check — Whether processes were killed, zombie processes, refusal to stop
  │
  └─ Step 4: Post-Stop Verification — Process disappeared, port released, no residuals
```

## Step 1: Pre-Stop Status Check

**Goal**: Confirm the component's running status before the stop operation is executed, determining whether there are factors preventing the stop

### 1.1 Active Connection Check

Check whether the component currently has active connections; active connections may cause the stop operation to block:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Based on the `port` table in the component config file, execute this check for each port to determine whether external connections are persistently occupying.

### 1.2 Running Task Check

Check the component logs for currently executing long-running tasks (e.g., large queries, data writes):

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["running","executing","query","transaction","batch","longrunning"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 1.3 HA Role Status Check (HA components only)

Check the current Active/Standby role of the HA component; stopping the Active node may trigger active/standby switchover:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Pre-Stop Status Assessment**:

| Status Item | Normal | Risk | Suggestion |
|-------------|--------|------|------------|
| Active connections | None or few | Large number of persistent connections | Investigate connection source, wait for release or force disconnect |
| Running tasks | No long tasks | Long-running tasks present | Wait for tasks to complete before stopping |
| HA role | Stopping Standby node | Stopping Active node | Perform active/standby switchover first, then stop the original Active node |

---

## Step 2: Stop Execution Check

**Goal**: Confirm whether the stop command was correctly transmitted from Controller to NodeAgent and executed

### 2.1 Controller Stop Operation Logs

Check the Controller logs for stop operation related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","stop","kill","terminate","ERROR","failed","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common ERROR Keywords**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Failed to send stop command | Command not delivered to NodeAgent | Check NodeAgent status and network |
| Stop timeout | Stop operation timed out | Process refuses to stop or is stuck, proceed to Step 3 |
| Agent timeout | Agent response timed out | NodeAgent abnormal or under high load |
| Operation rejected | Operation rejected | Current state does not allow stop (e.g., another operation in progress) |

### 2.2 NodeAgent Stop Execution Logs

Check the NodeAgent logs for stop operation execution:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","ProcessAction","stop","kill","ERROR","fail","timeout","signal"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 2.3 NodeAgent Stop Script Execution Logs

Check the stop script execution:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","stop","kill","signal","ERROR","fail","exit","refused"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer stop command dispatch failed |
| Normal | Has ERROR | — | NodeAgent layer stop execution abnormal |
| Normal | Normal | Has ERROR | Stop script execution failed, proceed to Step 3 |
| Normal | Normal | Normal | Stop command executed, proceed to Steps 3-4 for verification |

---

## Step 3: Process Exit Check

**Goal**: Confirm whether processes have correctly exited, identifying zombie processes, D-state processes, or processes refusing to stop

### 3.1 Process Status Check

Based on the `process name` in the component config file, check whether the process still exists and its status:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file.

**Process Status Analysis**:

| Process Status | Meaning | Conclusion | Handling Suggestion |
|----------------|---------|------------|---------------------|
| Process does not exist | Exited normally | Stop successful | Proceed to Step 4 for verification |
| R (Running) | Still running | Process did not respond to stop signal | Check whether kill signal was delivered |
| D (Uninterruptible sleep) | Waiting for I/O | Process stuck in kernel-space I/O | Wait for I/O to complete or reboot node |
| Z (Zombie) | Zombie process | Child process exited but was not reaped | Find parent process and handle it |
| T (Stopped) | Paused | Process paused but not exited | Send SIGKILL to force terminate |

### 3.2 Zombie Process and D-State Process Check

Check whether zombie processes (Z state) or D-state (uninterruptible sleep) processes exist:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file, analyzing the process running status (R/D/Z/T) in the returned results.

> **Note**: D-state processes are usually stuck in I/O operations (e.g., disk read/write, NFS waiting).
> In this case, ordinary kill -9 cannot terminate them; the underlying I/O issue needs to be investigated or the node needs to be rebooted.

### 3.3 Child Process Residual Check

Check whether there are child processes that were not stopped (parent process exited but child processes still running):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

Check whether there are residual child processes in the process tree with `<service_name>`-related processes as parent nodes.

### 3.4 Kill Signal Delivery Check

Check the NodeAgent logs for kill signal sending records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","SIGTERM","SIGKILL","kill","signal","9","15","sent","deliver"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

---

## Step 4: Post-Stop Verification

**Goal**: Confirm that the component has been completely stopped, with no residual processes or port occupation

### 4.1 Process Disappearance Verification

Based on the `process name` in the component config file, confirm that all related processes no longer exist:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file. Expected result: process does not exist.

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

### 4.3 Residual Resource Check

Check whether there are residual lock files, PID files, or temporary files:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","stop","cleanup","pid","lock","remove","rm","residual"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 4.4 HA Status Verification (HA components only)

Confirm that the HA resource status after stop meets expectations:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Post-Stop Verification Results**:

| Check Item | Expected Result | Abnormal Result | Conclusion |
|------------|-----------------|------------------|------------|
| Process | Does not exist | Still exists | Stop failed, return to Step 3 |
| Port | Not listening | Still listening | Process not fully exited or residuals exist |
| Residual files | Cleaned up | PID/lock files exist | Stop script did not complete cleanup |
| HA status | Resource migrated/stopped | Resource abnormal | HA active/standby switchover abnormal |

### 4.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Stop` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Process stuck (Zombie/D-state) | Process status is Z or D, kill signal ineffective | D-state requires investigating I/O issues or rebooting node; Z-state requires finding parent process to reap |
| Kill signal not delivered | NodeAgent logs have no SIGTERM/SIGKILL records | Check communication between NodeAgent and process, manually send kill signal |
| Child processes not stopped | Parent process exited but child processes remain | Check whether stop script handles child processes, manually kill residual child processes |
| HA active/standby switchover triggered | Stopping Active node caused automatic failover | Manually switch to Standby first, then stop original Active node |
| Long-running task blocking stop | Component logs have executing queries/transactions | Wait for tasks to complete or terminate tasks before stopping |
| Stop script execution failed | Script logs have ERROR/fail | Check stop script logic and permissions |
| Active connections occupying port | Port check shows connections still exist | Investigate connection source, disconnect then retry stop |
| I/O wait causing D-state process | Process stuck on disk/NFS I/O | Investigate storage fault, reboot node if necessary |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Stop target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | Process names for each role of the component |
| <port_number> | Component config file | Ports for each role of the component |
| <log_directory> | Component config file | Log paths for each role of the component |
| <log_file_name> | Component config file | Log file names for each role of the component |
