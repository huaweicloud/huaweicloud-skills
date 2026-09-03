# Start Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Start Condition Check
  │
  ├─ Step 2: Start Execution Check
  │
  ├─ Step 3: Health Check Result
  │
  └─ Step 4: Post-Start Verification
```

## Step 1: Pre-Start Condition Check

**Goal**: Confirm that pre-start dependencies, configuration, ports, and other prerequisites are met, ruling out start failure due to unmet conditions.

### 1.1 Dependency Service Readiness Check

Based on the `dependency` table in the component config file, check whether each dependency service is running normally.
For strong dependency services, first confirm whether their processes exist:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<dependency_process_name>"}' \
  -p 'node_name=<node_name>'
```

> Execute this check for each strong dependency service's process name in the component config file's `dependency` table.

Also check whether the dependency service port is listening:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<dependency_port>"}' \
  -p 'node_name=<node_name>'
```

### 1.2 Configuration File Existence Check

Check the NodeAgent script logs for configuration file related errors, confirming that required configuration files for startup have been generated and content is correct:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","config","krb5.conf","configurations","ERROR","fail","not found","missing"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Config file not found | Configuration file not generated or accidentally deleted | Regenerate configuration file, refer to install.md Step 2 |
| Permission denied | Insufficient configuration file permissions | Check configuration file owner and permissions |
| Parse config failed | Configuration file format error or missing parameters | Check configuration template and parameter completeness |

### 1.3 Port Occupancy Check

Based on the `port` table in the component config file, check whether each port is already occupied (old process not stopped):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

> Execute this check for each port listed in the component config file's `port` table. Before startup, the port should **not be occupied**; if the port is already listening, it means the old process has not been stopped, and the old process needs to be stopped first.

### 1.4 Disk and Memory Check

Confirm sufficient node resources before startup:

```bash
# Disk space
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'

# Memory
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=memory-usage' \
  -p 'node_name=<node_name>'
```

**Abnormality Criteria**:

| Resource Metric | Threshold | Conclusion |
|-----------------|-----------|------------|
| Disk usage ≥ 100% | Disk full | Clean up disk; disk full will cause write log/data failure during startup |
| Disk usage ≥ 85% | Disk nearly full | Clean up disk space |
| Memory usage ≥ 95% | Insufficient memory | Free memory, otherwise OOM may occur after startup |

---

## Step 2: Start Execution Check

**Goal**: Confirm that the start command was correctly transmitted from Controller to NodeAgent and executed, locating errors in the start execution phase.

### 2.1 Controller Start Logs

Check the Controller logs for start operation related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","start","ERROR","failed","timeout","Exception","reject"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common ERROR Keywords**:

| ERROR Keyword | Meaning | Possible Cause |
|---------------|---------|-----------------|
| Failed to send command to agent | Command not delivered to NodeAgent | NodeAgent abnormal or network disconnected |
| Agent timeout | Agent response timed out | Agent stuck or under high load |
| Operation rejected | Operation rejected | Current state does not allow start (e.g., stopping/installing in progress) |
| Service already running | Service already running | Old process not stopped, need to stop first then start |

### 2.2 NodeAgent Execution Logs

Check the NodeAgent logs for start execution related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","ProcessAction","start","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 2.3 NodeAgent Script Execution Logs

Check the NodeAgent script logs for start script execution related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","start","ERROR","fail","exit","permission","port"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer fault, operation not dispatched |
| Normal | Has ERROR | — | NodeAgent layer fault, command not executed |
| Normal | Normal | Has ERROR | Script execution layer fault, start script failed |
| Normal | Normal | Normal | Continue with Steps 3-4 |

---

## Step 3: Health Check Result

**Goal**: Confirm whether the health check after startup passed, locating the cause of health check timeout or failure.

### 3.1 Process Existence Check

Based on the `process name` in the component config file, check whether the process has been started after startup:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

> Execute this check for each process name listed in the component config file. After startup, the process **should exist**; if the process does not exist, it means the start script execution failed or the process exited immediately after starting.

### 3.2 Port Listening Check

Based on the `port` table in the component config file, check whether the port is listening after startup:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

> After startup, the port **should be listening**; if the port is not listening but the process exists, it means component initialization is not complete or there is an internal error.

### 3.3 Health Check Logs

Check the NodeAgent script logs for health check timeout related content:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","health","check","timeout","unhealthy","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Also check the component's own runtime logs for start and health check related errors (based on the component config file's `log path` table):

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception","FATAL","fail","start","timeout","OOM","OutOfMemory"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Health check timeout | Health check timed out | Investigate whether the process truly started, check internal initialization time |
| Process not ready | Process started but not ready | Check component logs, confirm whether the initialization phase is stuck |
| OOM / OutOfMemory | Process killed due to insufficient memory | Expand memory or adjust component JVM parameters |
| Port already in use | Port conflict | Stop the old process occupying the port, then restart |

---

## Step 4: Post-Start Verification

**Goal**: Confirm that the component is running normally after startup, with correct HA status.

### 4.1 Process and Port Verification

Re-confirm process running and port listening status (same as Steps 3.1, 3.2):

```bash
# Process check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'

# Port check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

> Post-start verification criteria: Process **should exist** and port **should be listening**.

### 4.2 HA Resource Status Verification (HA components only)

For HA components (e.g., DBService, KrbServer, etc.), check whether the HA resource status is normal:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**HA Status Evaluation**:

| HA Status | Meaning | Normal? |
|-----------|---------|---------|
| Master | Master node running normally | Yes |
| Slave | Standby node running normally | Yes |
| Stopped | Resource not running | No, start failed |
| Failed | Resource fault | No, further investigation needed |
| Standby | Pending switchover state | Needs evaluation based on active/standby |

### 4.3 Network Connectivity Verification

Check network connectivity between the component process and dependency services:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-connectivity-test' \
  -p 'node_name=<node_name>'
```

### 4.4 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Start` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Port conflict (old process not stopped) | port-check shows port already occupied | Stop old process first, confirm port released, then restart |
| Health check timeout | Script logs have health check timeout | Investigate whether the process truly started, check why initialization phase is stuck |
| Configuration file missing | Script logs have config not found / missing | Regenerate configuration file, refer to install.md Step 2 |
| Permission issue | Script logs have Permission denied | Check owner and permissions of configuration files, data directories, PID files |
| Dependency service not ready | Dependency service process or port check failed | Start dependency service first, confirm ready, then start this component |
| Disk full | disk-space check shows ≥100% | Clean up disk space, ensure log and data directories are writable |
| OOM | Component logs have OutOfMemory / process disappears immediately after startup | Expand memory or adjust component memory parameters (e.g., JVM heap size) |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Start target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <process_name> | Component config file | e.g., krb5kdc, kadmind, gaussdb |
| <port_number> | Component config file | e.g., 21732, 21730 |
| <log_directory> | Component config file | Component runtime log directory |
| <log_file_name> | Component config file | Component runtime log file name |
| <dependency_process_name> | Component config file dependency table | Strong dependency service process name |
| <dependency_port> | Component config file dependency table | Strong dependency service port |
