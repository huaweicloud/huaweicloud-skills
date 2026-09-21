# MRS Manager API Client

## Overview

`manager_api_client.py` is an MRS Manager REST API client. It defines endpoints through YAML config files and supports HTTP Basic Auth and Cookie (JSESSIONID) authentication, encrypted password storage, and extensible API definitions.

It is used by the **manager mode** of this skill: when `scripts/manager_api_config.yaml` exists and `auth.encrypted_password` is set, `check_api_mode.py` returns `manager`, and the diagnosis reads the knowledge base under `fault_layer_manager/`, `scenarios_manager/`, and `propagation_manager.md`, and runs `manager_api_client.py` commands instead of the LakeWatch client.

## Files

| File | Description |
|------|-------------|
| `scripts/manager_api_client.py` | Main script: argument parsing, authentication management, API invocation |
| `scripts/manager_api_config.yaml` | Main config: service endpoint, auth info (API definitions are split into the subdirectory) |
| `scripts/manager_api_apis/` | API definition directory, grouped by function module |
| `scripts/manager_api_apis/session.yaml` | Session APIs |
| `scripts/manager_api_apis/cluster.yaml` | Cluster APIs |
| `scripts/manager_api_apis/host.yaml` | Host APIs |
| `scripts/manager_api_apis/alarm.yaml` | Alarm APIs |
| `scripts/manager_api_apis/audit.yaml` | Audit APIs |
| `scripts/manager_api_apis/log.yaml` | Log search/browse APIs |
| `scripts/manager_api_apis/monitor.yaml` | Monitor metric APIs |
| `scripts/manager_api_apis/service.yaml` | Service APIs |
| `scripts/manager_api_apis/instance.yaml` | Instance APIs |
| `scripts/manager_api_apis/stack.yaml` | Stack collection APIs |
| `scripts/manager_api_apis/command.yaml` | Command APIs |
| `scripts/manager_api_apis/health_check.yaml` | Health check APIs |
| `scripts/manager_api_apis/tool.yaml` | Tool APIs |
| `scripts/manager_api_apis/report.yaml` | Report APIs |
| `scripts/manager_api_apis/system.yaml` | System/OMS APIs |
| `scripts/manager_api_apis/permission.yaml` | User permission APIs |

## First-Time Use

### 1. Encrypt the Password

```bash
python3 scripts/manager_api_client.py --encrypt-password
```

It interactively prompts for the password (no echo). Paste the output ciphertext into `auth.encrypted_password` in `manager_api_config.yaml`.

### 2. Configure the Manager Endpoint

Set the Manager floating IP in `server.host` and port (default 28443) in `manager_api_config.yaml`. To obtain the floating IP:

1. On the OMS node run: `grep float_ip /opt/huawei/Bigdata/om-server/OMS/workspace/conf/oms.ini`
2. Or on the primary OMS node: `ip addr | grep <known OMS subnet>` (the floating IP is on the primary OMS node)
3. Or ask the cluster administrator

### 3. Verify an API Call

```bash
python3 scripts/manager_api_client.py -a get_oms_info --json
```

## Usage

### List All Available APIs

```bash
python3 scripts/manager_api_client.py --list-apis
```

### Query Cluster Alarms

```bash
python3 scripts/manager_api_client.py -a get_alarms -p 'status=1' --json
```

### Query Host Info

```bash
python3 scripts/manager_api_client.py -a get_hosts --json
python3 scripts/manager_api_client.py -a get_host_detail -p 'hostname=8-5-225-5' --json
```

### Query Instance Status

```bash
python3 scripts/manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=DBService' \
  --json
```

### Query Host Process Status

```bash
python3 scripts/manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' \
  --json
```

### Query Host Monitor Metrics

```bash
python3 scripts/manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' \
  --json
```

### Query Host Resource Usage

```bash
python3 scripts/manager_api_client.py -a get_host_resource \
  -p 'hostname=<node_name>' \
  --json
```

### Browse a Log File

```bash
python3 scripts/manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/controller/acs/acs.log' \
  -p 'start_line=1' \
  -p 'end_line=200' \
  --json
```

> The `file_name` parameter of `browse_log` must be the full path of the log file; relative paths or file names are not supported. Use `get_log_filename` first to obtain the exact file name when uncertain.

### Search Logs by Keyword

```bash
# Start a log search (returns task_id)
python3 scripts/manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'key_word=ERROR' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' \
  -p 'services=Manager:Manager:Agent' \
  -p 'min_log_level=ERROR' \
  --json

# Query the search progress and results
python3 scripts/manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' \
  --json
```

## Authentication Modes

| Mode | Parameter | Description |
|------|-----------|-------------|
| HTTP Basic Auth | `--auth basic` (default) | Every request carries the Authorization header; simple and direct, suitable for single calls |
| Cookie (JSESSIONID) | `--auth cookie` | Logs in via `login_check` first to obtain JSESSIONID; subsequent requests reuse it, suitable for batch calls |

### Cookie Mode Behavior

1. The first call automatically obtains a JSESSIONID through `login_check`
2. The cookie is cached to a local file (Win: `%TEMP%\manager_session\cookies.txt`, Linux: `/tmp/manager_session/cookies.txt`)
3. Subsequent calls reuse the cache if not expired (default 2 hours)
4. Expired cookies trigger automatic re-login
5. On 401/403, the cookie is refreshed automatically and the request retried once

## Password Encryption Mechanism

The encryption method is selected automatically based on the platform (`platform.system()`), no configuration needed:

| Platform | Encryption | Description |
|----------|-----------|-------------|
| Linux | CryptoAPI (SCC) | Production environment; keys managed by the security component |
| Windows | AES-256-CBC | Development environment; keys stored in the local `.aes_key` file |

> **Note**: Ciphertexts are not interchangeable between the two platforms; run `--encrypt-password` on the target platform separately.

## Dependencies

- Python 3.7+
- `pyyaml` - YAML parsing
- `cryptography` - Windows AES encryption

## Extending New APIs

Add a new API definition to the corresponding YAML file under `manager_api_apis/`; the script auto-loads all `.yaml`/`.yml` files in that directory at startup.

```yaml
apis:
  new_api_name:
    desc: "API description"
    method: "GET"
    path: "/api/v2/clusters/{cluster_id}/new-endpoint"
    timeout: 30
    required_params:
      - cluster_id
    optional_params:
      - param1
    param_rules:
      param1:
        type: str
        pattern: "^\\d{4}$"
        error: "param1 must be a 4-digit number"
    request_body_template:
      param1JsonKey: "{param1}"
```

## Common Parameters

| Parameter | Description |
|-----------|-------------|
| `-a, --api` | API name to call |
| `-p, --param` | API parameter in `key=value` form, repeatable |
| `-o, --output` | Download file save path (download APIs only) |
| `--auth` | Auth mode: `basic` or `cookie`, default `basic` |
| `--list-apis` | List all available APIs |
| `--encrypt-password` | Interactively input and encrypt the password, output ciphertext for the config file |
| `--json` | JSON formatted output |
| `--raw` | Raw response output (no formatting) |
| `--full` | Full return value (default is trimmed to the key fields configured in `response_filter`) |

## Parameter Format Rules

> **Important**:
> 1. Windows uses `python`, Linux uses `python3`
> 2. Every `-p` value MUST be wrapped in single quotes to prevent shell parsing of special characters
>
> **Windows (PowerShell)**: replace every `"` inside a value with `"""`:
> ```powershell
> -p 'keywords=["""ERROR"""]'
> -p 'user_data={"""userName""":"""test"""}'
> ```
>
> **Linux (bash)**: keep `"` as-is inside the value, wrap the whole value in single quotes:
> ```bash
> -p 'keywords=["ERROR","Exception"]'
> -p 'user_data={"userName":"test"}'
> ```

## Monitor Metric Names

MRS Manager API metric names use the `dev_` prefix, NOT the legacy names in the alarm docs. Use the `get_host_metric_definitions` API to query all metrics supported by the cluster.

### Common Metric Mapping

| Purpose | Legacy name (alarm docs) | Actual API name | Unit | Description |
|---------|--------------------------|-----------------|------|-------------|
| CPU usage | `cpu_usage_allhost` | `dev_cpu_surp_avg` | % | Total CPU usage |
| CPU user | `cpu_user_allhost` | `dev_cpu_us` | % | User-mode CPU |
| CPU system | `cpu_system_allhost` | `dev_cpu_sy` | % | Kernel-mode CPU |
| Load 1min | - | `dev_load_one_min` | - | 1-minute average load |
| Load 5min | - | `dev_load_five_min` | - | 5-minute average load |
| Load 15min | - | `dev_load_fifteen_min` | - | 15-minute average load |
| Disk usage (per disk) | `disk_usage_allhost` | `dev_disk_useage` | % | Note the spelling `useage`, not `usage` |
| Host disk usage | `disk_usage_allhost` | `dev_host_disk_usage` | % | Host-level summary |
| Disk IO utilization | - | `dev_disk_util` | % | IO utilization per disk |
| Disk read rate | `disk_read_allhost` | `dev_disk_read_byte_speed` | KB/s | |
| Disk write rate | `disk_write_allhost` | `dev_disk_write_byte_speed` | KB/s | |
| Swap usage | - | `dev_swap_used_ratio` | % | |
| File handle usage | - | `dev_file_used_ratio` | % | |

> `dev_disk_useage` and `dev_disk_util` are multi-object metrics (multiObject=true); the `object` field is the disk device name (e.g. `sda1`, `sdb1`), and each disk returns independent data.

### Query Metric Definitions

```bash
python3 scripts/manager_api_client.py -a get_host_metric_definitions -p 'hostname=<node_name>' --json
```

## Notes

1. **Python command**: Windows uses `python`, Linux uses `python3`.
2. **SSL verification**: skipped by default (Manager usually uses a self-signed certificate); set `verify_ssl: true` and configure `ca_cert` to verify.
3. **Manager connectivity**: the script runtime environment must be able to reach the Manager port 28443.
4. **HTTP timeout**: global timeout is `server.timeout` (default 60s); each API can override with its own `timeout` field.
5. **start_log_search parameters**: `services` format is `component:service:role` (e.g. `HDFS:HDFS:NameNode`), multiple separated by `;`; `key_word` must not contain command-injection characters such as `| ; & $ > < ' \ !`; `min_log_level` values: TRACE/DEBUG/INFO/WARN/ERROR/FATAL; `start_time`/`end_time` format: `yyyy-MM-ddTHH:mm:ss`.
6. **Mode selection**: Run `python3 scripts/check_api_mode.py` to determine whether this skill runs in manager mode or lakewatch mode. In manager mode use `manager_api_client.py`; in lakewatch mode use `lakewatch_api_client.py`.
