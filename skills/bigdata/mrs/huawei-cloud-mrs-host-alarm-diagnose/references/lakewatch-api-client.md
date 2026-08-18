# LakeWatch API Client

## Overview

`lakewatch_api_client.py` is a general-purpose LakeWatch API client. It defines endpoints through a YAML config file (`lakewatch_api_config.yaml`) and supports parameterized requests, automatic token management, and encrypted password storage.

## Files

| File | Description |
|------|-------------|
| `scripts/lakewatch_api_client.py` | Main script: argument parsing, token management, API invocation |
| `scripts/lakewatch_api_config.yaml` | Config file: service endpoint, auth info, API list |

## First-Time Use

### 1. Encrypt the Password

```bash
python3 scripts/lakewatch_api_client.py --encrypt-password
```

It interactively prompts for the password (no echo). Paste the output ciphertext into `auth.encrypted_password` in `lakewatch_api_config.yaml`.

### 2. Verify an API Call

Token acquisition is built-in and automatic on any API call:

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=xxx' \
  -p 'strategy_name=system-load'
```

## Usage

### List All Available APIs

```bash
python3 scripts/lakewatch_api_client.py --list-apis
```

### Collect Node Resource Data

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'strategy_name=system-load' \
  -p 'node_name=8-5-225-5'
```

Supported `strategy_name` values:

| Strategy | Description | Extra `env` |
|----------|-------------|-------------|
| `system-load` | System load | — |
| `memory-usage` | Memory usage | — |
| `disk-space` | Disk space | — |
| `disk-io` | Disk IO | — |
| `network-io` | Network IO | — |
| `file-handle` | File handle | — |
| `port-check` | Port check | `env={"PORT":"8080"}` |
| `log-disk-space` | Log disk space | — |
| `tmp-file` | Temporary file | — |
| `total-process-count` | Total process count | — |
| `high-cpu-processes` | High CPU processes | — |
| `high-memory-process` | High memory process | — |
| `zombie-process` | Zombie process | — |
| `dns-check` | DNS check | — |
| `network-interface-info` | Network interface info | — |
| `process-basic-info` | Process basic info | `env={"process_name":"java"}` |
| `process-file-descriptor` | Process file descriptor | `env={"PID":"12345"}` |
| `jstack-thread-dump` | JStack thread dump | `env={"PID":"<pid>"}` |
| `network-connectivity-test` | Network connectivity test | `env={"TARGET_IP":"<ip>"}` |
| `thread-statistics` | Thread statistics | — |
| `high-thread-process` | High thread process | — |
| `repetitive-processes` | Repetitive processes | — |
| `d-state-process` | D-state process | — |
| `process-status-distribution` | Process status distribution | — |
| `omm-process-tree` | OMM process tree | — |
| `process-network-connection` | Process network connection | — |
| `ha-resource-status` | HA resource status | — |
| `process-network-detail` | Process network detail | `env={"PID":"<pid>"}` |
| `network-adapter-config` | Network adapter config | `env={"NETWORK_ADAPTER_NAME":"<name>"}` |
| `disk-health-check` | Disk health check (block devices, read-only mounts, mount info, dmesg disk errors, soft RAID) | — |
| `disk-smart-info` | Disk SMART info | `env={"DISK_DEVICE":"/dev/sda"}` |
| `disk-raid-status` | Hard RAID status (logical disk + filtered physical disk info) | — |

### Collect Alarm Log Data

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'alarm_time=2026/06/11 16:00:32 GMT+08:00' \
  -p 'log_directory=/var/log/hadoop/hdfs' \
  -p 'log_file_name=hadoop-hdfs-datanode.log' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local'
```

When the log time format is non-standard ISO (e.g. `[2026-07-07 20:54:25,171]`), pass `time_pattern`:

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'alarm_time=2026/07/07 20:54:00 GMT+08:00' \
  -p 'log_directory=/var/log/Bigdata/omm/oms/pms' \
  -p 'log_file_name=pms*.log' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^\[([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||ymdHMS'
```

`time_pattern` format: `regex||format`. Use `(...)` capture groups in the regex to mark time fields; each char in the format describes one group: `y`=year `m`=month(number) `b`=month(English abbr Jan-Dec) `d`=day `H`=hour `M`=minute `S`=second `_`=skip. If `||` is absent, the default format is `ymdHMS`. Empty or `--` skips time filtering.

Common `time_pattern` values:

| Log Format | time_pattern |
|------------|--------------|
| `2026-07-07 20:54:25` | Not needed (default supported) |
| `[2026-07-07 20:54:25,171]` | `^\[([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})\|\|ymdHMS` |
| `[2026-07-07T10:10:26.380+0800]` | `^\[([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\|\|ymdHMS` |
| `07/May/2026:20:49:27 +0800` | `^([0-9]{2})/([A-Za-z]{3})/([0-9]{4}):([0-9]{2}):([0-9]{2}):([0-9]{2})\|\|dbyHMS` |
| `Dec 20 10:30:15` | `^([A-Za-z]{3}) +([0-9]{1,2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})\|\|bdHMS` |
| No time format | `--` |

### Proxy MRS Manager GET API

Through the LakeWatch `manager-access` proxy endpoint, you can remotely call MRS Manager GET APIs without directly accessing MRS Manager:

```bash
# Query audit dump config
python3 scripts/lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'target_url=api/v2/audits/config'

# Query audit logs (returns totalCount)
python3 scripts/lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'target_url=api/v2/audits?limit=1'
```

> `target_url` MUST NOT start with `/`. The proxy requires Agent >= 1.0.5 and reported OMS node info. Only GET is supported currently; PUT will be available after the Agent supports it.

### Query Alarm Skill

```bash
python3 scripts/lakewatch_api_client.py -a query_alarm_skill \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'alarm_sequence_id=1'
```

## Parameter Format

> **Important**:
> 1. Use `python` on Windows, `python3` on Linux.
> 2. Every `-p` value MUST be wrapped in single quotes to prevent shell parsing of special chars (`[]`, `{}`, `|`, `()`, etc.).
> 3. `alarm_time` format is `yyyy/MM/dd HH:mm:ss GMT+X:XX` (e.g. `2026/07/01 20:54:00 GMT+08:00`).

**Linux (bash)**:

```bash
-p 'cluster_id=xxx'
-p 'alarm_time=2026/07/07 20:54:00 GMT+08:00'
-p 'keywords=["ERROR","Exception"]'
-p 'env={"PORT":"20018|20019"}'
-p 'time_pattern=^\[([0-9]{4})-...'
```

**Windows (PowerShell)**: also wrap in single quotes, but every `"` inside a value must be replaced with `"""` (including `"` inside `[]` and `{}`):

```powershell
-p 'cluster_id=xxx'
-p 'alarm_time=2026/07/07 20:54:00 GMT+08:00'
-p 'keywords=["""ERROR""","""Exception"""]'
-p 'env={"""PORT""":"""20018|20019"""}'
-p 'env={"""PID""":"""392208"""}'
-p 'time_pattern=^\[([0-9]{4})-...'
```

## Token Management

Token acquisition is built into the script and handled automatically on API calls; users do not need to fetch it manually.

1. On an API call, the script uses the configured username + encrypted password to request a token.
2. The token is encrypted and cached locally (Win: `%TEMP%\lakewatch_token\token.json`, Linux: `/tmp/lakewatch_token/token.json`), with owner-only file permissions.
3. Subsequent calls reuse the cache; if not expired (default 1 day), the cached token is reused.
4. When the token expires, it is automatically re-fetched.

## Password Encryption

The encryption method is auto-selected by `platform.system()` (no configuration needed):

| Platform | Method | Note |
|----------|--------|------|
| Linux | CryptoAPI (SCC) | Production; key managed by the security component |
| Windows | AES-256-CBC | Dev; key stored in a local `.aes_key` file |

> The two ciphertexts are NOT interchangeable; run `--encrypt-password` on the platform where the skill will run.

### CryptoAPI (Linux)

Calls the CryptoAPI binary via `subprocess`: data in via stdin, result out via stdout, no shell pipe dependency.

### AES (Windows)

Uses `cryptography` library AES-256-CBC. The key is auto-generated on first encryption in `.aes_key` next to the script.

## Dependencies

- Python 3.7+
- `pyyaml` — YAML parsing
- `cryptography` — Windows AES encryption

## Extending New APIs

Add a new endpoint definition under the `apis` node in `lakewatch_api_config.yaml`:

```yaml
apis:
  new_api_name:
    method: "POST"
    path: "/v1/data-agent-lw/{cluster_id}/new-endpoint"
    timeout: 300
    required_params:
      - cluster_id
    optional_params:
      - param1
      - param2
    param_rules:
      param1:
        type: str
        pattern: "^\\d{4}$"
        error: "param1 must be 4 digits"
      param2:
        type: int
        min: 1
        max: 100
    request_body:
      param1: "param1JsonKey"
      param2: "param2JsonKey"
```

Then call it with `python3 lakewatch_api_client.py -a new_api_name -p 'cluster_id=xxx'`.

### Parameter Validation Rules

Configure `param_rules` to validate parameters; parameters without rules are not validated. Supported types:

| type | Config | Validation |
|------|--------|------------|
| `str` | `pattern`(regex), `error`(custom message) | Regex match; error if not matched |
| `int` | `min`, `max` | Convert to int + range check |
| `enum` | `values`(allowed list) | Value must be in the list |
| `path` | `prefix`(path prefix) | Forbid `..`, forbid consecutive separators `//`, restrict path prefix |

Example:

```yaml
param_rules:
  alarm_time:
    type: str
    pattern: "^\\d{4}/\\d{2}/\\d{2} \\d{2}:\\d{2}:\\d{2} GMT[+-]\\d{2}:\\d{2}$"
    error: "alarm_time format must be yyyy/MM/dd HH:mm:ss GMT+X:XX"
  log_type:
    type: enum
    values: ["local", "hdfs"]
  alarm_duration_minutes:
    type: int
    min: 1
  log_directory:
    type: path
    prefix: "/var/log/"
```

## Common Parameters

| Parameter | Description |
|-----------|-------------|
| `-a, --api` | API name to call |
| `-p, --param` | API parameter, format `key=value`, repeatable |
| `-o, --output` | Download file save path (download APIs only) |
| `--list-apis` | List all available APIs |
| `--encrypt-password` | Interactively input and encrypt a password; output ciphertext for the config file (password never appears in the process list) |
| `--json` | Output result in JSON format |

## Notes

1. **Python command**: use `python` on Windows, `python3` on Linux.
2. **Parameter quoting**: every `-p` value MUST be wrapped in single quotes to prevent shell parsing of special chars (`[]`, `{}`, `|`, `()`, etc.).
3. **Windows escaping**: on Windows PowerShell, every `"` inside a value must be replaced with `"""` (including `"` inside `[]` and `{}`, e.g. `["ERROR"]` -> `["""ERROR"""]`, `{"PID":"123"}` -> `{"""PID""":"""123"""}`).
4. **HTTP timeout**: global timeout is `server.timeout` (default 60s); each API can override it with the `timeout` field.
5. **collect_alarm_log_data**:
   - `alarm_time` format must be `yyyy/MM/dd HH:mm:ss GMT+X:XX` (e.g. `2026/07/01 20:54:00 GMT+08:00`).
   - `time_pattern` format is `regex||format`; use `(...)` capture groups in the regex; format chars: `y`=year `m`=month(number) `b`=month(English) `d`=day `H`=hour `M`=minute `S`=second `_`=skip. Default `ymdHMS` if `||` is absent.
