---
name: huawei-cloud-mrs-host-fault-diagnose
description: |
  Huawei Cloud MRS cluster fault diagnosis skill. Diagnoses service faults, instance faults, and host faults through progressive root cause localization: quick log scan first, host troubleshooting when host issues are found, detailed investigation when no conclusion is reached.
  Driven by the built-in LakeWatch API client and the per-component knowledge base under components/. No commands outside the knowledge base are fabricated.
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

**Architecture**: Caller (Agent) -> `lakewatch_api_client.py` (Python, scripts/) -> LakeWatch API -> MRS cluster (node resource data, logs, MRS Manager proxy); per-component knowledge base (components/<service_name>.md) drives the diagnosis flow; three fault layers (host -> instance -> service) with propagation chain tracing.

> **Note on language**: This SKILL.md and the documents under `references/` are written in English per the repository spec. The knowledge base documents under `fault_layer/`, `scenarios/`, `components/`, and `propagation.md` are also in English. Commands and code blocks are English throughout.

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

> This skill does NOT require KooCLI (`hcloud`). It calls the LakeWatch API through `scripts/lakewatch_api_client.py`. For the LakeWatch client setup, see [CLI Installation Guide](references/cli-installation-guide.md).

### 2. LakeWatch Credential Configuration

- A valid LakeWatch service account (username + password)
- The password MUST be encrypted with `--encrypt-password` and stored in `scripts/lakewatch_api_config.yaml` (`auth.encrypted_password`). Never store the plaintext password.
- **Security Rules**:
  - Never expose the LakeWatch password in conversation or command output
  - Never ask the user to input the plaintext password in conversation; use the interactive `--encrypt-password` flow
  - The token is cached locally with owner-only file permissions (Win: `%TEMP%\lakewatch_token\`, Linux: `/tmp/lakewatch_token/`)

### 3. Access Permissions

- Reachability to the LakeWatch service endpoint (configured in `scripts/lakewatch_api_config.yaml` `server.host`/`port`)
- The LakeWatch account must have permission to call the MRS Manager proxy and collect node resource/log data on the target cluster
- See [IAM Policies](references/iam-policies.md) for the access model and required roles

### 4. Dependent Skill: huawei-cloud-mrs-host-alarm-diagnose

This skill references the per-alarm diagnosis knowledge base from the **huawei-cloud-mrs-host-alarm-diagnose** skill (sibling directory under `skills/bigdata/mrs/`). When the fault diagnosis flow encounters a known alarm (12006/12007/25000/25500/27001), it loads the corresponding document from `../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md`.

- If the alarm skill exists, load the referenced document and follow its diagnosis flow
- If NOT exist, inform the user and proceed with the generic fault diagnosis flow
- The dependency is **document-level reference only** (loading markdown by relative path), NOT a direct skill call. Both skills share the same LakeWatch API client and config format.

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

## Workflow

### Step 1: Determine Fault Entry

Extract fault information from the user input and determine the diagnosis entry:

| User Description | Entry | Step 1 Action |
|-----------------|-------|----------------|
| Has `service_name`, no `node_name` (e.g. "KrbServer出问题了") | Service fault | Check all instance statuses, find faulty instances |
| Has `service_name` + `node_name` (e.g. "8-5-225-6上的KrbServer挂了") | Instance fault | Directly check that instance |
| Has `node_name`, no `service_name` (e.g. "8-5-225-6出问题了") | Host fault | Check host status, then check instances on the host |

### Step 2: Locate the Fault Object

#### Entry A: Service Fault (has service_name, no node_name)

Load `components/<service_name>.md` for component config. Query OMS primary/standby nodes, check process on each node:

```bash
python3 lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

**Decision**:

| Result | Next Step |
|--------|----------|
| All node processes normal | Step 4 detailed investigation |
| Some node processes missing | Step 3 quick log scan (for faulty nodes) |
| API call failed (node unreachable) | Step 4 host troubleshooting |

#### Entry B: Instance Fault (has service_name + node_name)

Load `components/<service_name>.md`. Directly check process on that node:

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

**Decision**:

| Result | Next Step |
|--------|----------|
| Process normal | Step 4 detailed investigation |
| Process missing | Step 3 quick log scan |
| API call failed (node unreachable) | Step 4 host troubleshooting |

#### Entry C: Host Fault (has node_name, no service_name)

Query OMS primary/standby nodes, query node IP, ping the faulty node from OMS active node:

```bash
python3 lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

```bash
python3 lakewatch_api_client.py -a query-node-ip \
  -p 'cluster_id=<cluster_id>' \
  -p 'node_name=<node_name>'
```

```bash
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ping-check' \
  -p 'env={"TARGET_IP":"<target_ip>"}' \
  -p 'node_name=<oms_active_node>'
```

**Decision**:

| Result | Next Step |
|--------|----------|
| Ping failed | Step 4 host troubleshooting (network/hardware) |
| Ping succeeded | Check all component processes on the host, find faulty instances -> Step 3 quick log scan |

### Step 3: Quick Log Scan

For the faulty node, quickly scan three layers of logs (Controller -> NodeAgent -> component), looking for clear ERROR:

```bash
# Controller log
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","timeout","Exception"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'

# NodeAgent script log
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

If `service_name` is known, also check the component's own log (path from `components/<service_name>.md`):

```bash
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

1. Load [Data Collection](scenarios/data_collection.md) to collect process/port/HA/resource/alarm/framework logs
2. Load [Instance Fault Diagnosis](fault_layer/instance_fault.md) for instance-level diagnosis (includes scenario identification)
3. If needed, load [Service Fault Diagnosis](fault_layer/service_fault.md) for service-level diagnosis
4. If host issue is found, load [Host Fault Diagnosis](fault_layer/host_fault.md) for host-level diagnosis

### Step 5: Propagation Chain Tracing

Load [Propagation Chain](propagation.md) to trace the root cause propagation path and impact scope.

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

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `cluster_id` | Required | MRS cluster ID | N/A |
| `service_name` | Conditionally required | Faulty component (required for service/instance fault entry) | N/A |
| `node_name` | Conditionally required | Faulty node (required for instance/host fault entry) | N/A |
| `alarm_time` | Optional | Fault occurrence time, format `yyyy/MM/dd HH:mm:ss GMT+X:XX` | Current time |
| `strategy_name` | Required by `collect_alarm_node_res_data` | Resource collection strategy | N/A |
| `log_directory` | Required by `collect_alarm_log_data` | Log directory, must be under `/var/log/` | N/A |
| `log_file_name` | Required by `collect_alarm_log_data` | Log file name, no path separators | N/A |
| `keywords` | Required by `collect_alarm_log_data` | Log keyword filter, JSON array | N/A |
| `log_type` | Required by `collect_alarm_log_data` | `local` or `hdfs` | N/A |
| `time_pattern` | Optional | Non-standard log time regex, format `regex\|\|format` | N/A |
| `target_url` | Required by `access_manager_get` | MRS Manager API path, must NOT start with `/` | N/A |

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
| [CLI Installation Guide](references/cli-installation-guide.md) | Python dependencies and LakeWatch client setup |
| [IAM Policies](references/iam-policies.md) | LakeWatch/MRS Manager access model and required roles |
| [Verification Method](references/verification-method.md) | Installation, configuration, and function verification |
| [Acceptance Criteria](references/acceptance-criteria.md) | Pass/fail criteria for skill testing |
| [Fault Diagnosis Workflow](references/fault-diagnosis-workflow.md) | Progressive fault diagnosis workflow design |
| [LakeWatch API Client](references/lakewatch-api-client.md) | Full API catalog, parameters, token and encryption mechanism |
| [Related Commands](references/related-commands.md) | Common LakeWatch API commands quick reference |
| **huawei-cloud-mrs-host-alarm-diagnose** (sibling skill) | **Dependency**: per-alarm diagnosis knowledge base (`../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md`). See Prerequisites section 4 for details. |
| [Data Collection](scenarios/data_collection.md) | Complete data collection flow (Step 4) |
| [Host Fault Diagnosis](fault_layer/host_fault.md) | Host layer diagnosis |
| [Instance Fault Diagnosis](fault_layer/instance_fault.md) | Instance layer diagnosis (includes scenario identification) |
| [Service Fault Diagnosis](fault_layer/service_fault.md) | Service layer diagnosis |
| [Propagation Chain](propagation.md) | Root cause propagation path tracing |
| [Common Scenario](scenarios/common.md) | 6-phase common diagnosis framework for all scenarios |
| `scenarios/<scenario>.md` | Scenario-specific checks (install/start/stop/uninstall/reinstall/reinstall_host/scale_out/scale_in) |
| `components/<service_name>.md` | Per-component configuration (process, port, log path, etc.) |
| `components/_template.md` | Template for new component configuration |

## Notes

- **Security**: This skill is read-only. It never exposes the LakeWatch password; the password is encrypted via `--encrypt-password` and stored in `lakewatch_api_config.yaml`. Repair steps are suggestions only.
- **No KooCLI**: This skill does not use `hcloud`; it calls the LakeWatch API through `lakewatch_api_client.py`. Do not mix in `hcloud` commands.
- **Command failure**: When a command fails, skip the current check item and continue with the other checks; do not abort the whole diagnosis.
- **Known limitations**: The `access_manager_get` proxy only supports GET requests (PUT is not yet available on the Agent side); `collect_alarm_log_data` requires `log_directory` to be under `/var/log/`; some `strategy_name` values require extra `env` parameters.
- **Cross-skill dependency**: This skill references alarm diagnosis documents from the huawei-cloud-mrs-host-alarm-diagnose skill (e.g. `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12006.md`, `12007.md`). See [Prerequisites section 4](#4-dependent-skill-huawei-cloud-mrs-host-alarm-diagnose) for the dependency declaration and handling rules. If the alarm skill is not installed, inform the user and proceed with the generic fault diagnosis flow.
