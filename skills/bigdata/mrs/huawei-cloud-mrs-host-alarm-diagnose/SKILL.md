---
name: huawei-cloud-mrs-host-alarm-diagnose
description: |
  Huawei Cloud MRS cluster alarm diagnosis skill. Analyzes the root cause of an MRS alarm based on user-provided alarm information (alarm ID, alarm name, alarm details, occurrence time, node IP, related service and logs), then outputs the root cause, repair steps, and verification method.
  Diagnosis is driven by the built-in LakeWatch API client and the per-alarm knowledge base under alarms/. No commands outside the knowledge base are fabricated.
  Applicable to MRS alarm diagnosis and root cause localization scenarios where an alarm ID is provided.
  Trigger words: "告警诊断", "告警定位", "alarm diagnosis", "alarm diagnose", "MRS告警", "告警原因", "告警ID", "alarm ID", "root cause"
tags: [huawei-cloud, mrs, alarm, diagnostics, troubleshooting]

# ============================================================
# Internal extension fields
# ============================================================
trigger:
  keywords: ["告警诊断", "告警定位", "MRS告警", "告警原因", "告警分析", "alarm diagnosis", "alarm diagnose", "alarm ID", "root cause", "alarm troubleshooting"]
  resource_types: ["MRS::cluster", "MRS::alarm"]
  hypotheses: ["alarm_triggered"]

input_schema:
  required:
    - name: "alarm_name"
      type: "string"
      description: "Alarm Chinese name, e.g. PMS进程异常"
    - name: "alarm_time"
      type: "string"
      description: "Alarm occurrence time, format yyyy/MM/dd HH:mm:ss GMT+X:XX, e.g. 2026/06/11 16:00:32 GMT+08:00"
  optional:
    - name: "alarm_id"
      type: "string"
      description: "Alarm unique ID, e.g. 12089. Required to locate the per-alarm knowledge base under alarms/"
    - name: "cluster_id"
      type: "string"
      description: "MRS cluster ID, e.g. fd04c789-39d4-4847-8fc9-4572fec9414f"
    - name: "node_name"
      type: "string"
      description: "Host name where the alarm occurred (from the alarm location info). A value containing '.' is a node IP; otherwise it is a host name"
    - name: "server_name"
      type: "string"
      description: "Service that raised the alarm (from the alarm location info), e.g. Manager"
    - name: "role_name"
      type: "string"
      description: "Role that raised the alarm (from the alarm location info), e.g. pms"
    - name: "additional_info"
      type: "string"
      description: "Alarm additional information, usually contains key diagnostic clues"

output_schema:
  - name: "diagnosis_report"
    type: "string"
    description: "Markdown diagnosis report containing alarm metadata, root cause, repair steps, and verification method"

allowed-tools:
  - bash
---

# Huawei Cloud MRS Alarm Diagnosis Skill

## Overview

This skill diagnoses Huawei Cloud MRS (MapReduce Service) cluster alarms. Given alarm information (alarm ID, alarm name, occurrence time, cluster ID, node, related service/role), it locates the root cause and outputs repair steps and a verification method.

**Architecture**: Caller (Agent) → `lakewatch_api_client.py` (Python, scripts/) → LakeWatch API → MRS cluster (node resource data, logs, MRS Manager proxy); per-alarm knowledge base (alarms/<alarm_id>.md) drives the diagnosis flow.

> **Note on language**: This SKILL.md, the documents under `references/`, and the per-alarm knowledge base under `alarms/` are all written in English per the repository spec. Commands and code blocks are English throughout.

**Applicable Scenarios**:
- An MRS cluster raises an alarm and the root cause must be located
- An on-call engineer needs guided, per-alarm diagnostic steps
- Alarm triage where an alarm ID is provided

**Typical Use Cases**:
- "MRS集群收到12089告警，帮忙诊断一下"
- "PMS进程异常告警，告警ID 12007，集群ID xxx，帮我定位原因"
- "Audit log dump failed alarm 12001, diagnose the root cause"
- "节点间网络互通异常，告警ID 12089，发生时间 2026/06/11 16:00:32 GMT+08:00"

## Critical Constraints

> **Important constraints:**
> 1. **Read-only**: This skill only runs information-gathering commands (view logs, query status). It MUST NOT run any start/stop, modify, or delete operations.
> 2. **User confirmation for repair**: The skill only provides executable repair steps; it MUST NOT directly execute any repair operation. All repair actions require user confirmation.
> 3. **Strict execution**: Diagnose strictly according to the per-alarm knowledge base content. Fabricating diagnostic commands outside the knowledge base is prohibited.

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
| Quoting | Every `-p` value MUST be wrapped in single quotes to prevent shell parsing of `[] {} | ()` | `-p 'keywords=["ERROR"]'` |

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

### Step 1: Determine Alarm Information

Extract the following alarm information from the user input:

| Field | Parameter | Required | Description | Example |
|-------|-----------|----------|-------------|---------|
| Alarm ID | `alarm_id` | Optional | Alarm unique ID, e.g. 12089 | `12007` |
| Alarm name | `alarm_name` | Required | Alarm Chinese name | `PMS进程异常` |
| Occurrence time | `alarm_time` | Required | Alarm occurrence time | `2026/06/11 16:00:32 GMT+08:00` |
| Cluster ID | `cluster_id` | Optional | MRS cluster ID | `fd04c789-39d4-4847-8fc9-4572fec9414f` |
| Host name | `node_name` | Optional | Host where the alarm occurred (from the alarm location info) | `8-5-225-6` |
| Service name | `server_name` | Optional | Service that raised the alarm (from the alarm location info) | `Manager` |
| Role name | `role_name` | Optional | Role that raised the alarm (from the alarm location info) | `pms` |
| Additional info | `additional_info` | Optional | Alarm additional information, usually contains key diagnostic clues | |

**Notes**:
- A node value containing `.` is a node IP; otherwise it is a host name.
- If the user does not provide the alarm ID or cluster ID, ask the user to provide the relevant information and stop execution.

### Step 2: Locate the Per-Alarm Knowledge Base

Based on the alarm ID, read `alarms/<alarm_id>.md` under this skill directory to get the diagnosis flow for that alarm. Also read [LakeWatch API Client](references/lakewatch-api-client.md) for the Python script usage.

If no matching alarm document exists, tell the user: `暂不支持此告警的分析。` (This alarm is not supported for analysis.)

### Step 3: Execute Alarm Diagnosis

Follow the per-alarm knowledge base from Step 2 to execute the diagnosis.

**Diagnosis execution notes**:
- Use only the specific commands provided in the per-alarm knowledge base; do not infer log paths yourself
- Variable placeholders (e.g. `<alarm_time>`, `<alarm_node>`) MUST be substituted with actual values, never hardcoded
- Command execution results MUST be summarized with a summarization tool
- When running `lakewatch_api_client.py`, use `python` on Windows and `python3` on Linux
- All `-p` parameter values MUST be wrapped in single quotes; on Windows PowerShell, every `"` inside a value must be replaced with `"""`
- **Important**: After diagnosis, reflect on the diagnosis results to confirm whether the alarm diagnosis is complete

**Command failure handling**: When a command fails, skip the current check item and continue with the other checks.

### Step 4: Output the Diagnosis Conclusion

Output following the template below:

```markdown
## Diagnosis Result

| Item | Content |
|------|---------|
| Diagnosis time | [time] |
| Cluster ID | [cluster_id] |
| Alarm name | [alarm_name] |
| Alarm ID | [alarm_id] |
| Alarm node | [node info] |
| Alarm occurrence time | [occurrence time] |

### Root Cause

**Preliminary judgment**: [root cause type]

**Analysis basis**:

- [basis 1]
- [basis 2]

### Repair Suggestion

| Priority | Operation | Description | Needs user confirmation |
|----------|-----------|-------------|-------------------------|
| 1 | [operation 1] | [description] | Yes |
| 2 | [operation 2] | [description] | Yes |
```

## Core Commands

### Query Alarm Skill Content

```bash
# Query the alarm diagnosis skill content by alarm sequence ID
python3 lakewatch_api_client.py -a query_alarm_skill \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_sequence_id=<alarm_serial_no>'
```

### Collect Alarm Node Resource Data

```bash
# Collect node resource data for a given strategy (system-load, memory-usage, disk-space, etc.)
python3 lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

Supported `strategy_name` values include: `system-load`, `memory-usage`, `disk-space`, `disk-io`, `network-io`, `file-handle`, `port-check` (needs `env={"PORT":"<port>"}`), `high-cpu-processes`, `high-memory-process`, `zombie-process`, `dns-check`, `network-connectivity-test` (needs `env={"TARGET_IP":"<ip>"}`), `process-basic-info` (needs `env={"process_name":"java"}`), `process-file-descriptor` (needs `env={"PID":"<pid>"}`), `jstack-thread-dump` (needs `env={"PID":"<pid>"}`), `disk-health-check`, `disk-smart-info` (needs `env={"DISK_DEVICE":"/dev/sda"}`), `disk-raid-status`, `ha-resource-status`, and more. See [LakeWatch API Client](references/lakewatch-api-client.md) for the full list.

### Collect Alarm Log Data

```bash
# Collect alarm-related log data around the alarm time
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=2026/06/11 16:00:32 GMT+08:00' \
  -p 'log_directory=/var/log/hadoop/hdfs' \
  -p 'log_file_name=hadoop-hdfs-datanode.log' \
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
# Query audit dump config via the LakeWatch manager-access proxy
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/audits/config'

# Query audit logs (returns totalCount)
python3 lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/audits?limit=1'
```

> `target_url` MUST NOT start with `/`. The proxy requires Agent >= 1.0.5 and reported OMS node info. Only GET is supported currently.

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `alarm_id` | Optional | Alarm unique ID, used to locate `alarms/<alarm_id>.md` | N/A |
| `alarm_name` | Required | Alarm Chinese name | N/A |
| `alarm_time` | Required | Alarm occurrence time, format `yyyy/MM/dd HH:mm:ss GMT+X:XX` | N/A |
| `cluster_id` | Optional | MRS cluster ID | N/A |
| `node_name` | Optional | Alarm node host name or IP | N/A |
| `server_name` | Optional | Service that raised the alarm | N/A |
| `role_name` | Optional | Role that raised the alarm | N/A |
| `additional_info` | Optional | Alarm additional information | N/A |
| `strategy_name` | Required by `collect_alarm_node_res_data` | Resource collection strategy | N/A |
| `log_directory` | Required by `collect_alarm_log_data` | Log directory, must be under `/var/log/` | N/A |
| `log_file_name` | Required by `collect_alarm_log_data` | Log file name, no path separators | N/A |
| `keywords` | Required by `collect_alarm_log_data` | Log keyword filter, JSON array | N/A |
| `log_type` | Required by `collect_alarm_log_data` | `local` or `hdfs` | N/A |
| `time_pattern` | Optional | Non-standard log time regex, format `regex||format` | N/A |

## Output Format

The diagnosis report is output in Markdown, containing:
- **Diagnosis result table**: diagnosis time, cluster ID, alarm name, alarm ID, alarm node, alarm occurrence time
- **Root cause**: preliminary judgment + analysis basis (each basis cited from actual command output)
- **Repair suggestion table**: priority, operation, description, needs-user-confirmation (all repair actions require user confirmation)

See the template in the [Workflow → Step 4](#step-4-output-the-diagnosis-conclusion) section.

## Verification Method

See [Verification Method](references/verification-method.md) for the installation, configuration, and function verification steps.

## Best Practices

1. **Locate the knowledge base first**: Always confirm the alarm ID and read `alarms/<alarm_id>.md` before running any command; do not infer diagnostic steps yourself.
2. **Substitute placeholders**: Replace `<cluster_id>`, `<alarm_time>`, `<node_name>`, `<target_ip>`, etc. with actual user-provided values; never hardcode them.
3. **Quote parameters**: Always wrap `-p` values in single quotes; on Windows PowerShell, escape `"` as `"""` to avoid `code:500` errors.
4. **Time format**: `alarm_time` must follow `yyyy/MM/dd HH:mm:ss GMT+X:XX`; for non-standard log time formats, pass `time_pattern`.
5. **Summarize results**: Use a summarization tool to condense command output before analysis; large raw outputs should not be analyzed directly.
6. **Reflect after diagnosis**: After completing the checks, reflect on whether the root cause is confirmed; if not, re-check the per-alarm flow for missed steps.
7. **Read-only**: All commands are read-only; repair steps are suggestions only and require user confirmation before execution.

## References

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | Python dependencies and LakeWatch client setup |
| [IAM Policies](references/iam-policies.md) | LakeWatch/MRS Manager access model and required roles |
| [Verification Method](references/verification-method.md) | Installation, configuration, and function verification |
| [Acceptance Criteria](references/acceptance-criteria.md) | Pass/fail criteria for skill testing |
| [LakeWatch API Client](references/lakewatch-api-client.md) | Full API catalog, parameters, token and encryption mechanism |
| [Related Commands](references/related-commands.md) | Common LakeWatch API commands quick reference |
| `alarms/<alarm_id>.md` | Per-alarm diagnosis knowledge base (mirrors the MRS product alarm catalog) |

## Notes

- **Security**: This skill is read-only. It never exposes the LakeWatch password; the password is encrypted via `--encrypt-password` and stored in `lakewatch_api_config.yaml`. Repair steps are suggestions only.
- **No KooCLI**: This skill does not use `hcloud`; it calls the LakeWatch API through `lakewatch_api_client.py`. Do not mix in `hcloud` commands.
- **Command failure**: When a command fails, skip the current check item and continue with the other checks; do not abort the whole diagnosis.
- **Known limitations**: The `access_manager_get` proxy only supports GET requests (PUT is not yet available on the Agent side); `collect_alarm_log_data` requires `log_directory` to be under `/var/log/`; some `strategy_name` values require extra `env` parameters.
