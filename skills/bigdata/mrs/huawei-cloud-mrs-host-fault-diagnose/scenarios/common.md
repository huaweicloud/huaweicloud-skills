# Common Scenario Diagnosis Flow

> This file defines the diagnostic framework shared by all operation scenarios. Each scenario file (install.md, etc.) defines scenario-specific check steps.
> All scenario diagnoses follow the 6-phase structure below, combining common checks with scenario-specific checks to achieve end-to-end diagnosis.

## Diagnosis Phase Overview

```
Phase 1: Operation Confirmation — Confirm operation type, target component, target node, operation time
  │
  ├─ Phase 2: Controller Execution Chain Check — Controller logs → NodeAgent logs → Script logs
  │
  ├─ Phase 3: Target Node Resource Check — Disk/Memory/CPU/Network
  │
  ├─ Phase 4: Component Process and Port Check — Process existence, port listening, HA status
  │
  ├─ Phase 5: Component Log Check — ERROR in component's own runtime logs
  │
  └─ Phase 6: Scenario-Specific Checks — Load scenarios/<scenario>.md to execute scenario-specific diagnostic steps
```

## Phase 1: Operation Confirmation

**Goal**: Confirm that the input parameters for diagnosis are complete

**Parameters**:

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| scenario | Required | Scenario type: install/uninstall/reinstall/reinstall_host/start/stop/scale_out/scale_in | start |
| cluster_id | Required | MRS cluster ID | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| service_name | Required | Component service name | KrbServer |
| node_name | Optional | Target node name (required for install/scale_out) | 8-5-225-6 |
| alarm_time | Optional | Operation occurrence time | 2026/08/15 15:00:00 GMT+08:00 |

**Steps**:

1. Load the component config file `components/<service_name>.md` to obtain process names, ports, log paths, and other information
2. If the component config file does not exist, inform the user that the component is not yet supported, and explain how to add it via _template.md
3. Query OMS active/standby node information to determine the Active OMS node

```bash
python lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

4. Set `oms_active_node` to the returned activeNode value

---

## Phase 2: Controller Execution Chain Check

**Goal**: Confirm whether the operation command was correctly transmitted from Controller to NodeAgent and executed

### 2.1 Controller Operation Logs

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","ERROR","failed","timeout","Exception"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common ERROR Keywords**:

| ERROR Keyword | Meaning | Possible Cause |
|---------------|---------|-----------------|
| Failed to send command to agent | Command not delivered to NodeAgent | NodeAgent abnormal or network disconnected |
| Agent timeout | Agent response timed out | Agent stuck or under high load |
| Config generate failed | Configuration generation failed | Configuration template error or missing parameters |
| Operation rejected | Operation rejected | Current state does not allow this operation |
| Install package not found | Installation package missing | Package not distributed or accidentally deleted |

### 2.2 NodeAgent Execution Logs (only when node_name is known)

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","ProcessAction","ERROR","fail","start","stop","install","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 2.3 NodeAgent Script Execution Logs

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer fault |
| Normal | Has ERROR | — | NodeAgent layer fault |
| Normal | Normal | Has ERROR | Script execution layer fault |
| Normal | Normal | Normal | Continue with Phases 3-6 |

---

## Phase 3: Target Node Resource Check

**Goal**: Rule out operation failure due to insufficient resources

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

# CPU load
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

**Abnormality Criteria**:

| Resource Metric | Threshold | Conclusion |
|-----------------|-----------|------------|
| Disk usage ≥ 100% | Disk full | Clean up disk or expand capacity |
| Disk usage ≥ 85% | Disk nearly full | Clean up disk |
| Memory usage ≥ 95% | Insufficient memory | Free memory or expand capacity |
| CPU load ≥ cores × 2 | CPU overloaded | Investigate high-CPU processes |

---

## Phase 4: Component Process and Port Check

**Goal**: Confirm component process status and port listening status

### 4.1 Process Check

Based on the `process name` in the component config file, check each role's process:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file.

### 4.2 Port Check

Based on the `port` table in the component config file, check each port:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

### 4.3 HA Resource Status (HA components only)

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Result Mapping** (criteria differ by scenario):

| Scenario | Process Should Exist | Process Should Not Exist | Description |
|----------|---------------------|--------------------------|-------------|
| install/reinstall | No (before install) → Yes (after auto-start) | — | Process should not exist before install; should exist after auto-start |
| uninstall | — | Yes | Process should not exist after uninstall |
| start | Yes | — | Process should exist after start |
| stop | — | Yes | Process should not exist after stop |
| scale_out | Yes (except new node) | — | No residual processes should exist on expansion node |
| scale_in | Yes (remaining nodes) | — | No processes should exist on scaled-in node |

---

## Phase 5: Component Log Check

**Goal**: Check for errors in the component's own runtime logs

Based on the `log path` table in the component config file, check each role's log directory:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception","fail","FATAL","PANIC"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

---

## Phase 6: Scenario-Specific Checks

Load `scenarios/<scenario>.md` and execute the scenario-specific diagnostic steps.

The check points defined in the scenario file reference information from the component config file (ports, log paths, data directories, etc.),
so different components will automatically use different check parameters under the same scenario.
