# Start Scenario Diagnosis (start)

> Prerequisites: The common check phases 1-5 of common.md have been completed
> Component config: load `components/<service_name>.md` to obtain component information

## Diagnosis Flow

```
Step 1: Pre-Start Condition Check
  │
  ├─ Step 2: Start Execution Check
  │
  ├─ Step 3: Health Check Results
  │
  └─ Step 4: Post-Start Verification
```

## Step 1: Pre-Start Condition Check

**Goal**: Confirm that prerequisites such as dependencies, configurations, and ports are satisfied before start, ruling out start failures caused by unsatisfied conditions.

### 1.1 Dependency Service Readiness Check

Based on the `dependency` table in the component config file, check whether each dependency service is running normally.
For strong dependency services, first confirm that their processes exist:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

> Execute this check for the process name of each strong dependency service in the `dependency` table of the component config file.

Also check whether the dependency service ports are listening:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

### 1.2 Configuration File Existence Check

Check the NodeAgent script logs for errors related to the configuration file, and confirm that the config file required for start has been generated with correct content:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common Problems**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|---------------|-------------------|
| Config file not found | Config file not generated or accidentally deleted | Regenerate the config file, see install.md Step 2 |
| Permission denied | Insufficient config file permissions | Check the config file owner and permissions |
| Parse config failed | Config file format error or missing parameters | Check the config template and parameter completeness |

### 1.3 Port Occupancy Check

Based on the `port` table in the component config file, check whether each port is already occupied (by an old process that has not been stopped):

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

> Execute this check for each port in the `port` table of the component config file. Before start, the port should **not be occupied**; if the port is already listening, it means the old process has not been stopped, and the old process needs to be stopped first.

### 1.4 Disk and Memory Check

Confirm that the node resources are sufficient before start:

```bash
# Disk space
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json

# Memory
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Abnormality Criteria**:

| Resource Metric | Threshold | Conclusion |
|-----------------|-----------|------------|
| Disk usage ≥ 100% | Disk full | Clean up disk; a full disk will cause start-time log/data write failures |
| Disk usage ≥ 85% | Disk nearly full | Clean up disk space |
| Memory usage ≥ 95% | Insufficient memory | Free memory, otherwise OOM may occur after start |

---

## Step 2: Start Execution Check

**Goal**: Confirm that the start command was correctly transmitted from Controller to NodeAgent and executed, locating errors during the start execution phase.

### 2.1 Controller Start Logs

Check the Controller logs for errors related to the start operation:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common ERROR Keywords**:

| ERROR Keyword | Meaning | Possible Cause |
|---------------|---------|-----------------|
| Failed to send command to agent | Command not delivered to NodeAgent | NodeAgent abnormal or network disconnected |
| Agent timeout | Agent response timed out | Agent stuck or under high load |
| Operation rejected | Operation rejected | Current state does not allow start (e.g. stopping/installing in progress) |
| Service already running | Service already running | Old process not stopped; stop it first, then start |

### 2.2 NodeAgent Execution Logs

Check the NodeAgent logs for errors related to start execution:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 2.3 NodeAgent Script Execution Logs

Check the NodeAgent script logs for errors related to start script execution:

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
| Has ERROR | — | — | Controller layer fault, operation not dispatched |
| Normal | Has ERROR | — | NodeAgent layer fault, command not executed |
| Normal | Normal | Has ERROR | Script execution layer fault, start script failed |
| Normal | Normal | Normal | Continue with Steps 3-4 |

---

## Step 3: Health Check Results

**Goal**: Confirm whether the health check after start passed, locating the cause of health check timeout or failure.

### 3.1 Process Existence Check

Based on the `process name` in the component config file, check whether the process has been pulled up after start:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

> Execute this check for each process name listed in the component config file. After start, the process **should exist**; if the process does not exist, it means the start script failed or the process exited immediately after starting.

### 3.2 Port Listening Check

Based on the `port` table in the component config file, check whether the ports are listening after start:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

> After start, the port **should be listening**; if the port is not listening but the process exists, it means component initialization is incomplete or an internal error occurred.

### 3.3 Health Check Logs

Check the NodeAgent script logs for content related to health check timeout:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Also check the component's own runtime logs for errors related to start and health check (based on the `log path` table of the component config file):

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=ERROR' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

**Common Problems**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|---------------|-------------------|
| Health check timeout | Health check timed out | Investigate whether the process actually started; check the internal initialization duration |
| Process not ready | Process not ready after starting | Check the component logs to confirm whether the initialization phase is stuck |
| OOM / OutOfMemory | Process killed due to insufficient memory | Expand memory or adjust the component JVM parameters |
| Port already in use | Port conflict | Stop the old process occupying the port, then restart |

---

## Step 4: Post-Start Verification

**Goal**: Confirm that the component is running normally after start and the HA status is correct.

### 4.1 Process and Port Verification

Re-confirm the process running and port listening status (same as Steps 3.1 and 3.2):

```bash
# Process check
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json

# Port check
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

> Post-start verification standard: the process **should exist** and the port **should be listening**.

### 4.2 HA Resource Status Verification (HA components only)

For HA components (such as DBService, KrbServer, etc.), check whether the HA resource status is normal:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**HA Status Criteria**:

| HA Status | Meaning | Normal? |
|-----------|---------|---------|
| Master | Primary node running normally | Yes |
| Slave | Standby node running normally | Yes |
| Stopped | Resource not running | No, start failed |
| Failed | Resource fault | No, further investigation needed |
| Standby | Pending failover state | Depends on primary/standby status |

### 4.3 Network Connectivity Verification

Check the network connectivity between the component process and its dependency services:

```bash
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<target_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

### 4.4 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Start (start)` section of the component config file,
load the component config and execute each check item.

For each check item, choose the appropriate API call based on the check content it describes:
- Process/port check → `get_host_process`
- Log check → `browse_log` / `start_log_search`
- HA status → `get_instances`

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristic | Repair Suggestion |
|------------|---------------|-------------------|
| Port conflict (old process not stopped) | port-check shows the port already occupied | Stop the old process first, confirm the port is released, then restart |
| Health check timeout | Script log has health check timeout | Investigate whether the process actually started; check the cause of the stuck initialization phase |
| Config file missing | Script log has config not found / missing | Regenerate the config file, see install.md Step 2 |
| Permission problem | Script log has Permission denied | Check the owner and permissions of the config file, data directory, and PID file |
| Dependency service not ready | Dependency service process or port check failed | Start the dependency service first, confirm it is ready, then start this component |
| Disk full | disk-space check shows ≥100% | Clean up disk space, ensure the log and data directories are writable |
| OOM | Component log has OutOfMemory / process disappears immediately after starting | Expand memory or adjust the component memory parameters (such as JVM heap size) |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Start target node |
| <oms_active_node> | common.md Phase 1 | OMS primary node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | Such as krb5kdc, kadmind, gaussdb |
| <port> | Component config file | Such as 21732, 21730 |
| <log_directory> | Component config file | Component runtime log directory |
| <log_file_name> | Component config file | Component runtime log file name |
| <dependency_process_name> | Component config file dependency table | Process name of the strong dependency service |
| <dependency_port> | Component config file dependency table | Port of the strong dependency service |
