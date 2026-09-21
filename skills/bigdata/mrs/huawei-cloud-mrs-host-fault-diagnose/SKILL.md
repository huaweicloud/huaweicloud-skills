---
name: huawei-cloud-mrs-host-fault-diagnose
description: |
  Huawei Cloud MRS cluster fault diagnosis skill. Diagnoses service faults, instance faults, and host faults through progressive root cause localization: quick log scan first, host troubleshooting when host issues are found, detailed investigation when no conclusion is reached.
  Diagnosis is driven by the built-in LakeWatch API client (lakewatch mode) or the MRS Manager API client (manager mode) and the per-layer knowledge base under fault_layer/ and scenarios/ (lakewatch) or fault_layer_manager/ and scenarios_manager/ (manager). The API mode is auto-detected by check_api_mode.py. No commands outside the knowledge base are fabricated.
  Applicable to MRS fault diagnosis and root cause localization scenarios where a service name or node name is provided.
  Trigger words: "故障诊断", "故障定位", "fault diagnosis", "fault diagnose", "MRS故障", "服务故障", "实例故障", "主机故障", "集群排查", "集群诊断", "启动失败", "停止异常", "KrbServer故障", "DBService故障", "fault troubleshooting"
tags: [huawei-cloud, mrs, fault, diagnostics, troubleshooting]

# ============================================================
# Internal extension fields
# ============================================================
trigger:
  keywords: ["故障诊断", "故障定位", "MRS故障", "服务故障", "实例故障", "主机故障", "集群排查", "集群诊断", "启动失败", "停止异常", "KrbServer故障", "DBService故障", "fault diagnosis", "fault diagnose", "fault troubleshooting"]
  resource_types: ["MRS::cluster", "MRS::service", "MRS::instance", "MRS::host"]
  hypotheses: ["service_fault", "instance_fault", "host_fault"]

input_schema:
  required:
    - name: "cluster_id"
      type: "string"
      description: "MRS cluster ID, e.g. 77b54fac-5e03-4713-9ac9-835d02d54e67"
  optional:
    - name: "service_name"
      type: "string"
      description: "Faulty component service name (required for service/instance fault entry). e.g. KrbServer"
    - name: "node_name"
      type: "string"
      description: "Faulty node name (required for instance/host fault entry). A value containing '.' is a node IP; otherwise it is a host name. e.g. 8-5-225-6"
    - name: "alarm_time"
      type: "string"
      description: "Fault occurrence time, format yyyy/MM/dd HH:mm:ss GMT+X:XX. Defaults to current time if not provided. e.g. 2026/08/17 15:00:00 GMT+08:00"

output_schema:
  - name: "diagnosis_report"
    type: "string"
    description: "Markdown diagnosis report containing fault metadata, diagnosis process, propagation path, root cause, and repair suggestions"

allowed-tools:
  - bash
---

# Huawei Cloud MRS Host Fault Diagnosis Skill

## Overview

This skill diagnoses Huawei Cloud MRS (MapReduce Service) cluster faults. Given a service name and/or node name, it progressively localizes the root cause: quick log scan first, host troubleshooting when host issues are found, detailed investigation when no conclusion is reached.

**Architecture**: Caller (Agent) -> `check_api_mode.py` (Python, scripts/) determines the API mode -> either `lakewatch_api_client.py` -> LakeWatch API -> MRS cluster (node resource data, logs, MRS Manager proxy) or `manager_api_client.py` -> MRS Manager REST API (28443). Per-layer knowledge base (`fault_layer/` + `scenarios/` + `propagation.md` in lakewatch mode; `fault_layer_manager/` + `scenarios_manager/` + `propagation_manager.md` in manager mode) drives the diagnosis flow; per-component config under `components/` is shared by both modes; three fault layers (host -> instance -> service) with propagation chain tracing.

> **Note on language**: This SKILL.md and the documents under `references/` are written in English per the repository spec. The knowledge base documents under `fault_layer/`, `fault_layer_manager/`, `scenarios/`, `scenarios_manager/`, `components/`, `propagation.md`, and `propagation_manager.md` are also in English. Commands and code blocks are English throughout.

**Applicable Scenarios**:
- A service is reported unhealthy and the root cause must be localized
- An instance is reported faulty on a specific node
- A host is reported unreachable or abnormal
- Progressive fault triage from quick scan to deep investigation

**Typical Use Cases**:
- "KrbServer出问题了，帮忙诊断一下" (service fault, no node specified)
- "8-5-225-6上的KrbServer挂了" (instance fault, service + node specified)
- "8-5-225-6出问题了" (host fault, node only)
- "MRS集群KrbServer启动失败，集群ID xxx"
- "DBService停止异常，节点8-5-225-6"

## Critical Constraints

> **Important constraints:**
> 1. **Read-only**: This skill only runs information-gathering commands (view logs, query status, collect resource data). It MUST NOT run any start/stop, modify, or delete operations.
> 2. **User confirmation for repair**: The skill only provides executable repair suggestions; it MUST NOT directly execute any repair operation. All repair actions require user confirmation.
> 3. **Strict execution**: Diagnose strictly according to the knowledge base content under this skill directory. Fabricating diagnostic commands outside the knowledge base is prohibited.

## Prerequisites

### 1. Python Requirements

- Python >= 3.7
- Dependencies: `pyyaml` (YAML parsing), `cryptography` (Windows AES password encryption only)
- Linux uses CryptoAPI for password encryption (no `cryptography` dependency)
- Verify installation: `python3 --version` (Linux) / `python --version` (Windows)

> This skill does NOT require KooCLI (`hcloud`). It calls the LakeWatch API through `scripts/lakewatch_api_client.py` (lakewatch mode) or the MRS Manager REST API through `scripts/manager_api_client.py` (manager mode). For the client setup, see [CLI Installation Guide](references/cli-installation-guide.md).

### 2. LakeWatch Credential Configuration

- A valid LakeWatch service account (username + password)
- The password MUST be encrypted with `--encrypt-password` and stored in `scripts/lakewatch_api_config.yaml` (`auth.encrypted_password`). Never store the plaintext password.
- **Security Rules**:
  - Never expose the LakeWatch password in conversation or command output
  - Never ask the user to input the plaintext password in conversation; use the interactive `--encrypt-password` flow
  - The token is cached locally with owner-only file permissions (Win: `%TEMP%\lakewatch_token\`, Linux: `/tmp/lakewatch_token/`)

### 3. MRS Manager Credential Configuration (Manager Mode)

Manager mode is enabled when `scripts/manager_api_config.yaml` exists and `auth.encrypted_password` is set.

- A valid MRS Manager account (username + password)
- Configure the Manager floating IP in `server.host` (port default 28443). To obtain it, run `grep float_ip /opt/huawei/Bigdata/om-server/OMS/workspace/conf/oms.ini` on the OMS node, or ask the cluster administrator.
- The password MUST be encrypted with `python3 scripts/manager_api_client.py --encrypt-password` and stored in `scripts/manager_api_config.yaml` (`auth.encrypted_password`). Never store the plaintext password.
- **Security Rules**:
  - Never expose the Manager password in conversation or command output
  - Never ask the user to input the plaintext password in conversation; use the interactive `--encrypt-password` flow
  - Windows AES ciphertext requires the `.aes_key` file to be migrated together to decrypt on another machine; Linux SCC ciphertext is not portable across clusters
- See [MRS Manager API Client](references/manager-api-client.md) for the full client usage.

### 4. Access Permissions

- **Lakewatch mode**: Reachability to the LakeWatch service endpoint (configured in `scripts/lakewatch_api_config.yaml` `server.host`/`port`); the LakeWatch account must have permission to call the MRS Manager proxy and collect node resource/log data on the target cluster
- **Manager mode**: The script runtime environment must be able to reach the Manager port 28443; the Manager account needs read permissions on alarm, host, instance, and log APIs
- See [IAM Policies](references/iam-policies.md) for the access model and required roles

### 5. Dependent Skill: huawei-cloud-mrs-host-alarm-diagnose

This skill references the per-alarm diagnosis knowledge base from the **huawei-cloud-mrs-host-alarm-diagnose** skill (sibling directory under `skills/bigdata/mrs/`). When the fault diagnosis flow encounters a known alarm (12006/12007/25000/25500/27001), it loads the corresponding document: `../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md` in lakewatch mode, or `../huawei-cloud-mrs-host-alarm-diagnose/alarm_manager/<alarm_id>.md` in manager mode.

- If the alarm skill exists, load the referenced document and follow its diagnosis flow
- If NOT exist, inform the user and proceed with the generic fault diagnosis flow
- The dependency is **document-level reference only** (loading markdown by relative path), NOT a direct skill call. Both skills share the same LakeWatch/Manager API clients and config format.

## Command Format Standard

This skill uses the LakeWatch API client instead of KooCLI. The unified command format is:

```bash
# Linux
python3 <skill_dir>/scripts/lakewatch_api_client.py -a <api_name> -p 'key1=value1' -p 'key2=value2'

# Windows
python <skill_dir>/scripts/lakewatch_api_client.py -a <api_name> -p 'key1=value1' -p 'key2=value2'
```

| Element | Rule | Example |
|---------|------|---------|
| `python3` / `python` | Linux uses `python3`, Windows uses `python` | `python3 lakewatch_api_client.py` |
| `-a, --api` | API name to call (defined in `lakewatch_api_config.yaml`) | `-a collect_alarm_node_res_data` |
| `-p, --param` | API parameter in `key=value` form, repeatable | `-p 'cluster_id=xxx'` |
| Quoting | Every `-p` value MUST be wrapped in single quotes to prevent shell parsing of `[] {} \| ()` | `-p 'keywords=["ERROR"]'` |

**Windows (PowerShell) quote rule**: every `"` inside a value must be replaced with `"""` (including `"` inside `[]` and `{}`), otherwise the server returns `{"message":"Unknown exception","success":false,"code":"500"}`:

```powershell
# Correct on Windows
-p 'keywords=["""ERROR"""]'
-p 'env={"""PID""":"""123"""}'

# Wrong on Windows (will fail)
-p 'keywords=["ERROR"]'
```

**Linux (bash) quote rule**: keep `"` as-is inside the value, wrap the whole value in single quotes:

```bash
# Correct on Linux
-p 'keywords=["ERROR","Exception"]'
-p 'env={"PID":"123"}'
```

For the full API catalog, parameters, and the token/encryption mechanism, see [LakeWatch API Client](references/lakewatch-api-client.md).

### MRS Manager API Client (Manager Mode)

When `check_api_mode.py` reports `manager`, use `manager_api_client.py` instead of the LakeWatch client. The unified command format is:

```bash
# Linux
python3 <skill_dir>/scripts/manager_api_client.py -a <api_name> -p 'key1=value1' -p 'key2=value2' --json

# Windows
python <skill_dir>/scripts/manager_api_client.py -a <api_name> -p 'key1=value1' -p 'key2=value2' --json
```

| Element | Rule | Example |
|---------|------|---------|
| `python3` / `python` | Linux uses `python3`, Windows uses `python` | `python3 manager_api_client.py` |
| `-a, --api` | API name to call (defined in `manager_api_apis/`) | `-a get_instances` |
| `-p, --param` | API parameter in `key=value` form, repeatable | `-p 'service_name=KrbServer'` |
| `--json` | JSON formatted output | `--json` |
| `--auth` | Auth mode: `basic` (default) or `cookie` | `--auth cookie` |
| Quoting | Same quote rules as the LakeWatch client (`'` wrapping; Windows `"` -> `"""`) | `-p 'keywords=["ERROR"]'` |

For the full API catalog, authentication modes, metric names, and password encryption mechanism, see [MRS Manager API Client](references/manager-api-client.md).

## Workflow

### Step 0: Determine the API Mode

Run the mode check script to determine whether diagnosis is based on MRS Manager or LakeWatch:

- **Windows**: `python scripts/check_api_mode.py`
- **Linux**: `python3 scripts/check_api_mode.py`

The script checks whether `scripts/manager_api_config.yaml` exists and whether `encrypted_password` is filled in, and returns a JSON result:

```json
{"mode": "manager", "reason": "..."}     // manager-based
{"mode": "lakewatch", "reason": "..."}   // lakewatch-based
```

Rules:
- `manager_api_config.yaml` does not exist -> default **lakewatch**
- File exists but `encrypted_password` is empty -> default **lakewatch**
- File exists and `encrypted_password` is not empty -> **manager**

**The mode determines which knowledge base directories to load throughout the workflow**:

| Mode | Command script | Fault layer | Scenarios | Propagation | Alarm docs (sibling skill) |
|------|----------------|-------------|-----------|-------------|----------------------------|
| lakewatch | `lakewatch_api_client.py` | `fault_layer/` | `scenarios/` | `propagation.md` | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/` |
| manager | `manager_api_client.py` | `fault_layer_manager/` | `scenarios_manager/` | `propagation_manager.md` | `../huawei-cloud-mrs-host-alarm-diagnose/alarm_manager/` |

In the rest of this SKILL.md, `<FAULT_LAYER>` denotes `fault_layer` (lakewatch) or `fault_layer_manager` (manager), `<SCENARIOS>` denotes `scenarios` (lakewatch) or `scenarios_manager` (manager), and `<PROPAGATION>` denotes `propagation.md` (lakewatch) or `propagation_manager.md` (manager).

### Step 1: Determine Fault Entry

Extract fault information from the user input and determine the diagnosis entry:

| User Description | Entry | Step 1 Action |
|-----------------|-------|----------------|
| Has `service_name`, no `node_name` (e.g. "KrbServer出问题了") | Service fault | Check all instance statuses, find faulty instances |
| Has `service_name` + `node_name` (e.g. "8-5-225-6上的KrbServer挂了") | Instance fault | Directly check that instance |
| Has `node_name`, no `service_name` (e.g. "8-5-225-6出问题了") | Host fault | Check host status, then check instances on the host |

### Step 2: Locate the Fault Object

> **Mode note**: The command blocks below show lakewatch-mode commands. In **manager mode**, use the corresponding `manager_api_client.py` commands — see [Core Commands -> Manager Mode Commands](#manager-mode-commands-manager-mode) and `<SCENARIOS>/data_collection.md` for the per-mode equivalents.

#### Entry A: Service Fault (has service_name, no node_name)

Load `components/<service_name>.md` for component config. Query OMS primary/standby nodes, check process on each node:

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

**Manager mode equivalents**: `get_oms_info` (OMS primary/standby nodes); `get_host_process` (process status).

**Decision**:

| Result | Next Step |
|--------|----------|
| All node processes normal | Step 4 detailed investigation |
| Some node processes missing | Step 3 quick log scan (for faulty nodes) |
| API call failed (node unreachable) | Step 4 host troubleshooting |

#### Entry B: Instance Fault (has service_name + node_name)

Load `components/<service_name>.md`. Directly check process on that node:

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

**Manager mode equivalent**: `get_host_process` (process status).

**Decision**:

| Result | Next Step |
|--------|----------|
| Process normal | Step 4 detailed investigation |
| Process missing | Step 3 quick log scan |
| API call failed (node unreachable) | Step 4 host troubleshooting |

#### Entry C: Host Fault (has node_name, no service_name)

Query OMS primary/standby nodes, query node IP, ping the faulty node from OMS active node:

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a query-node-ip \
  -p 'cluster_id=<cluster_id>' \
  -p 'node_name=<node_name>'
```

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ping-check' \
  -p 'env={"TARGET_IP":"<target_ip>"}' \
  -p 'node_name=<oms_active_node>'
```

**Manager mode equivalents**: `get_oms_info` (OMS primary/standby); `get_hosts -p 'hostname=<node_name>'` (node IP); `check_remote` (remote connectivity — no dedicated ping-check API).

**Decision**:

| Result | Next Step |
|--------|----------|
| Ping failed | Step 4 host troubleshooting (network/hardware) |
| Ping succeeded | Check all component processes on the host, find faulty instances -> Step 3 quick log scan |

### Step 3: Quick Log Scan

For the faulty node, quickly scan three layers of logs (Controller -> NodeAgent -> component), looking for clear ERROR:

```bash
# lakewatch mode - Controller log
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","timeout","Exception"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'

# lakewatch mode - NodeAgent script log
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Manager mode equivalents** (see `<SCENARIOS>/data_collection.md`): `browse_log` (Controller `exe.log`, NodeAgent `script.log`); `start_log_search` + `get_log_search_progress` (keyword search).

If `service_name` is known, also check the component's own log (path from `components/<service_name>.md`):

```bash
# lakewatch mode
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception","FATAL","fail","OOM"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Decision**:

| Log Result | Next Step |
|------------|-----------|
| Clear ERROR (e.g. OOM/permission/port conflict/config missing) | Output root cause |
| Log shows node unreachable / Agent timeout | Step 4 host troubleshooting |
| Multiple faulty nodes on same host | Step 4 host troubleshooting |
| No clear conclusion | Step 4 detailed investigation |

### Step 4: Detailed Investigation

When the quick log scan yields no conclusion, collect complete data:

1. Load [Data Collection](<SCENARIOS>/data_collection.md) to collect process/port/HA/resource/alarm/framework logs
2. Load [Instance Fault Diagnosis](<FAULT_LAYER>/instance_fault.md) for instance-level diagnosis (includes scenario identification)
3. If needed, load [Service Fault Diagnosis](<FAULT_LAYER>/service_fault.md) for service-level diagnosis
4. If host issue is found, load [Host Fault Diagnosis](<FAULT_LAYER>/host_fault.md) for host-level diagnosis

### Step 5: Propagation Chain Tracing

Load [Propagation Chain](<PROPAGATION>) to trace the root cause propagation path and impact scope.

### Step 6: Output Diagnosis Conclusion

```markdown
## Diagnosis Result

| Item | Content |
|------|---------|
| Diagnosis time | [time] |
| Cluster ID | [cluster_id] |
| Faulty component | [service_name] |
| Faulty node | [node_name] |

### Diagnosis Process

| Step | Result |
|------|--------|
| Instance status | [which nodes normal/abnormal] |
| Quick log scan | [found/not found clear ERROR] |
| Host troubleshooting | [normal/abnormal: ...] |
| Detailed investigation | [process/port/HA/resource results] |

### Propagation Path

[root cause] -> [propagation] -> [symptom] (single-layer root cause if no propagation)

### Root Cause Analysis

**Root cause layer**: [host/instance/service]
**Root cause type**: [specific reason]

### Repair Suggestion

| Priority | Operation | Description | Needs user confirmation |
|----------|-----------|-------------|-------------------------|
| 1 | [operation] | [description] | Yes |
```

## Core Commands

### Query OMS Primary/Standby Nodes

```bash
python3 lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

### Query Node IP

```bash
python3 lakewatch_api_client.py -a query-node-ip \
  -p 'cluster_id=<cluster_id>' \
  -p 'node_name=<node_name>'
```

### Collect Node Resource Data

```bash
# Process basic info
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'

# Port check
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port>"}' \
  -p 'node_name=<node_name>'

# HA resource status
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'

# Disk space / Memory / CPU load
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

Supported `strategy_name` values include: `system-load`, `memory-usage`, `disk-space`, `disk-io`, `network-io`, `file-handle`, `port-check`, `high-cpu-processes`, `high-memory-process`, `zombie-process`, `dns-check`, `network-connectivity-test`, `process-basic-info`, `process-file-descriptor`, `jstack-thread-dump`, `disk-health-check`, `disk-smart-info`, `ha-resource-status`, `omm-process-tree`, and more. See [LakeWatch API Client](references/lakewatch-api-client.md) for the full list.

### Collect Alarm Log Data

```bash
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local'
```

When the log time format is non-standard ISO (e.g. `[2026-07-07 20:54:25,171]`), pass `time_pattern`:

```bash
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=2026/07/07 20:54:00 GMT+08:00' \
  -p 'log_directory=/var/log/Bigdata/omm/oms/pms' \
  -p 'log_file_name=pms*.log' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^\[([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||ymdHMS'
```

### Proxy MRS Manager GET API

```bash
# Query cluster services
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services'

# Query host processes
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/hosts/<node_name>/processes'

# Query active alarms
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/alarms'
```

> `target_url` MUST NOT start with `/`. The proxy requires Agent >= 1.0.5 and reported OMS node info. Only GET is supported currently.

### Manager Mode Commands (Manager Mode)

When `check_api_mode.py` reports `manager`, use `manager_api_client.py` for the equivalent queries:

```bash
# Query OMS primary/standby nodes
python3 manager_api_client.py -a get_oms_info --json

# Query cluster services
python3 manager_api_client.py -a get_cluster_services \
  -p 'cluster_id=<cluster_id>' --json

# Query host detail (disk/memory/CPU usage)
python3 manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json

# Query host process status
python3 manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json

# Query service instances (HA status)
python3 manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json

# Query host monitor metrics (dev_ prefix)
python3 manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' --json

# Check remote node connectivity (replaces ping-check/network-connectivity-test)
python3 manager_api_client.py -a check_remote \
  -p 'remote_ip=<target_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json

# Browse a log file (file_name must be a full path)
python3 manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json

# Search logs by keyword (returns task_id, then poll progress)
python3 manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'key_word=ERROR' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=<component>:<service_name>:<role_name>' \
  -p 'min_log_level=WARN' --json

python3 manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

> `start_log_search` `services` format: `component:service:role` (e.g. `HDFS:HDFS:NameNode`); `start_time`/`end_time` format: `yyyy-MM-ddTHH:mm:ss`. See [MRS Manager API Client](references/manager-api-client.md) for metric names and full parameter rules.

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `cluster_id` | Required | MRS cluster ID | N/A |
| `service_name` | Conditionally required | Faulty component (required for service/instance fault entry) | N/A |
| `node_name` | Conditionally required | Faulty node (required for instance/host fault entry) | N/A |
| `alarm_time` | Optional | Fault occurrence time, format `yyyy/MM/dd HH:mm:ss GMT+X:XX` | Current time |
| `strategy_name` | Required by `collect_alarm_node_res_data` | Resource collection strategy (lakewatch mode) | N/A |
| `log_directory` | Required by `collect_alarm_log_data` | Log directory, must be under `/var/log/` (lakewatch mode) | N/A |
| `log_file_name` | Required by `collect_alarm_log_data` | Log file name, no path separators (lakewatch mode) | N/A |
| `keywords` | Required by `collect_alarm_log_data` | Log keyword filter, JSON array (lakewatch mode) | N/A |
| `log_type` | Required by `collect_alarm_log_data` | `local` or `hdfs` (lakewatch mode) | N/A |
| `time_pattern` | Optional | Non-standard log time regex, format `regex\|\|format` (lakewatch mode) | N/A |
| `target_url` | Required by `access_manager_get` | MRS Manager API path, must NOT start with `/` (lakewatch mode) | N/A |
| `metric_names` | Required by `get_host_metrics` | Comma-separated monitor metric names with `dev_` prefix (manager mode) | N/A |
| `key_word` | Required by `start_log_search` | Log keyword to search (manager mode) | N/A |
| `current_time` | Required by `start_log_search` | Current time, format `yyyy-MM-ddTHH:mm:ss` (manager mode) | N/A |
| `file_name` | Required by `browse_log` | Full log file path (manager mode) | N/A |

## Output Format

The diagnosis report is output in Markdown, containing:
- **Diagnosis result table**: diagnosis time, cluster ID, faulty component, faulty node
- **Diagnosis process**: step-by-step results (instance status, quick log scan, host troubleshooting, detailed investigation)
- **Propagation path**: root cause -> propagation -> symptom (single-layer if no propagation)
- **Root cause analysis**: root cause layer (host/instance/service) + root cause type
- **Repair suggestion table**: priority, operation, description, needs-user-confirmation (all repair actions require user confirmation)

See the template in the [Workflow -> Step 6](#step-6-output-diagnosis-conclusion) section.

## Verification Method

See [Verification Method](references/verification-method.md) for the installation, configuration, and function verification steps.

## Best Practices

1. **Determine entry first**: Based on user-provided information (service_name, node_name), determine whether the entry is service fault, instance fault, or host fault before starting diagnosis.
2. **Progressive investigation**: Always start with quick log scan (Step 3); only escalate to detailed investigation (Step 4) when no clear conclusion is reached.
3. **Substitute placeholders**: Replace `<cluster_id>`, `<alarm_time>`, `<node_name>`, `<target_ip>`, `<process_name>`, etc. with actual user-provided values; never hardcode them.
4. **Quote parameters**: Always wrap `-p` values in single quotes; on Windows PowerShell, escape `"` as `"""` to avoid `code:500` errors.
5. **Time format**: `alarm_time` must follow `yyyy/MM/dd HH:mm:ss GMT+X:XX`; for non-standard log time formats, pass `time_pattern`.
6. **Summarize results**: Use a summarization tool to condense command output before analysis; large raw outputs should not be analyzed directly.
7. **Reflect after diagnosis**: After completing the checks, reflect on whether the root cause is confirmed; if not, re-check for missed steps.
8. **Read-only**: All commands are read-only; repair steps are suggestions only and require user confirmation before execution.
9. **Command failure handling**: When a command fails, skip the current check item and continue with the other checks; do not abort the whole diagnosis.

## References

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | Python dependencies and LakeWatch/Manager client setup |
| [IAM Policies](references/iam-policies.md) | LakeWatch/MRS Manager access model and required roles |
| [Verification Method](references/verification-method.md) | Installation, configuration, and function verification |
| [Acceptance Criteria](references/acceptance-criteria.md) | Pass/fail criteria for skill testing |
| [Fault Diagnosis Workflow](references/fault-diagnosis-workflow.md) | Progressive fault diagnosis workflow design |
| [LakeWatch API Client](references/lakewatch-api-client.md) | Full LakeWatch API catalog, parameters, token and encryption mechanism |
| [MRS Manager API Client](references/manager-api-client.md) | Full MRS Manager API catalog, authentication modes, metric names and encryption mechanism |
| [Related Commands](references/related-commands.md) | Common LakeWatch/Manager API commands quick reference |
| **huawei-cloud-mrs-host-alarm-diagnose** (sibling skill) | **Dependency**: per-alarm diagnosis knowledge base (`../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md` in lakewatch mode, `alarm_manager/<alarm_id>.md` in manager mode). See Prerequisites section 5 for details. |
| [Data Collection](scenarios/data_collection.md) | Complete data collection flow, lakewatch mode (Step 4) |
| [Data Collection (Manager)](scenarios_manager/data_collection.md) | Complete data collection flow, manager mode (Step 4) |
| [Host Fault Diagnosis](fault_layer/host_fault.md) | Host layer diagnosis, lakewatch mode |
| [Instance Fault Diagnosis](fault_layer/instance_fault.md) | Instance layer diagnosis (includes scenario identification), lakewatch mode |
| [Service Fault Diagnosis](fault_layer/service_fault.md) | Service layer diagnosis, lakewatch mode |
| [Host Fault Diagnosis (Manager)](fault_layer_manager/host_fault.md) | Host layer diagnosis, manager mode |
| [Instance Fault Diagnosis (Manager)](fault_layer_manager/instance_fault.md) | Instance layer diagnosis (includes scenario identification), manager mode |
| [Service Fault Diagnosis (Manager)](fault_layer_manager/service_fault.md) | Service layer diagnosis, manager mode |
| [Propagation Chain](propagation.md) | Root cause propagation path tracing, lakewatch mode |
| [Propagation Chain (Manager)](propagation_manager.md) | Root cause propagation path tracing, manager mode |
| [Common Scenario](scenarios/common.md) | 6-phase common diagnosis framework, lakewatch mode |
| [Common Scenario (Manager)](scenarios_manager/common.md) | 6-phase common diagnosis framework, manager mode |
| `scenarios/<scenario>.md` | Scenario-specific checks, lakewatch mode (install/start/stop/uninstall/reinstall/reinstall_host/scale_out/scale_in) |
| `scenarios_manager/<scenario>.md` | Scenario-specific checks, manager mode (install/start/stop/uninstall/reinstall/reinstall_host/scale_out/scale_in) |
| `components/<service_name>.md` | Per-component configuration (process, port, log path, etc.) — shared by both modes |
| `components/_template.md` | Template for new component configuration |

## Notes

- **Security**: This skill is read-only. It never exposes the LakeWatch or MRS Manager password; passwords are encrypted via `--encrypt-password` and stored in the corresponding config YAML. Repair steps are suggestions only.
- **No KooCLI**: This skill does not use `hcloud`; it calls the LakeWatch API through `lakewatch_api_client.py` or the MRS Manager REST API through `manager_api_client.py`. Do not mix in `hcloud` commands.
- **Mode switching**: Run `check_api_mode.py` (Step 0) to determine the mode. In manager mode use `manager_api_client.py` and the `fault_layer_manager/` + `scenarios_manager/` + `propagation_manager.md` knowledge base; in lakewatch mode use `lakewatch_api_client.py` and `fault_layer/` + `scenarios/` + `propagation.md`. Do not mix clients across modes.
- **Command failure**: When a command fails, skip the current check item and continue with the other checks; do not abort the whole diagnosis.
- **Known limitations**: The `access_manager_get` proxy only supports GET requests (PUT is not yet available on the Agent side); `collect_alarm_log_data` requires `log_directory` to be under `/var/log/`; some `strategy_name` values require extra `env` parameters; in manager mode `browse_log` requires the full log file path, `start_log_search` `services` must follow `component:service:role`, and `get_alarms` may return 500 on some Manager versions (fall back to Controller `exe.log` browsing).
- **Cross-skill dependency**: This skill references alarm diagnosis documents from the huawei-cloud-mrs-host-alarm-diagnose skill (`../huawei-cloud-mrs-host-alarm-diagnose/alarms/<id>.md` in lakewatch mode, `alarm_manager/<id>.md` in manager mode). See [Prerequisites section 5](#5-dependent-skill-huawei-cloud-mrs-host-alarm-diagnose) for the dependency declaration and handling rules. If the alarm skill is not installed, inform the user and proceed with the generic fault diagnosis flow.
