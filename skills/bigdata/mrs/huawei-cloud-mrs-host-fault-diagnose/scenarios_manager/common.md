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
  └─ Phase 6: Scenario-Specific Checks — Load <scenario>.md to execute scenario-specific diagnostic steps
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
python manager_api_client.py -a get_oms_info --json
```

4. Set `oms_active_node` to the returned activeNode value

---

## Phase 2: Controller Execution Chain Check

**Goal**: Confirm whether the operation command was correctly transmitted from Controller to NodeAgent and executed

### 2.1 Controller Operation Logs

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
| Config generate failed | Configuration generation failed | Configuration template error or missing parameters |
| Operation rejected | Operation rejected | Current state does not allow this operation |
| Install package not found | Installation package missing | Package not distributed or accidentally deleted |

### 2.2 NodeAgent Execution Logs (only when node_name is known)

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 2.3 NodeAgent Script Execution Logs

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
| Has ERROR | — | — | Controller layer fault |
| Normal | Has ERROR | — | NodeAgent layer fault |
| Normal | Normal | Has ERROR | Script execution layer fault |
| Normal | Normal | Normal | Continue with Phases 3-6 |

---

## Phase 3: Target Node Resource Check

**Goal**: Rule out operation failure due to insufficient resources

```bash
# Disk space
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json

# Memory
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json

# CPU load
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' --json
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
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file.

### 4.2 Port Check

Based on the `port` table in the component config file, check each port:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

### 4.3 HA Resource Status (HA components only)

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
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

---

## Phase 6: Scenario-Specific Checks

Load `<scenario>.md` and execute the scenario-specific diagnostic steps.

The check points defined in the scenario file reference information from the component config file (ports, log paths, data directories, etc.),
so different components will automatically use different check parameters under the same scenario.
