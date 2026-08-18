# Related Commands - MRS Alarm Diagnosis

Quick reference for the common LakeWatch API commands used by this skill. All commands use `python3` on Linux and `python` on Windows. Every `-p` value MUST be wrapped in single quotes; on Windows PowerShell, escape `"` as `"""`.

## General Format

```bash
python3 scripts/lakewatch_api_client.py -a <api_name> -p 'key1=value1' -p 'key2=value2'
```

## Utility Commands

```bash
# List all available APIs
python3 scripts/lakewatch_api_client.py --list-apis

# Encrypt the LakeWatch password (interactive, no echo)
python3 scripts/lakewatch_api_client.py --encrypt-password
```

## Alarm Lookup

```bash
# Query alarm diagnosis skill content by alarm sequence ID
python3 scripts/lakewatch_api_client.py -a query_alarm_skill \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_sequence_id=<alarm_serial_no>'

# Query alarm info by alarm sequence ID
python3 scripts/lakewatch_api_client.py -a query-alarm-info \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarmSequenceId=<alarm_serial_no>'
```

## Node Resolution

```bash
# Query node IP by node name
python3 scripts/lakewatch_api_client.py -a query-node-ip \
  -p 'cluster_id=<cluster_id>' \
  -p 'nodeName=<node_name>'

# Query cluster primary/standby node names
python3 scripts/lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

## Node Resource Data Collection

```bash
# System load
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=system-load' -p 'node_name=<node_name>'

# Memory usage
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=memory-usage' -p 'node_name=<node_name>'

# Disk space
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=disk-space' -p 'node_name=<node_name>'

# Disk IO
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=disk-io' -p 'node_name=<node_name>'

# Network IO
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=network-io' -p 'node_name=<node_name>'

# High CPU processes
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=high-cpu-processes' -p 'node_name=<node_name>'

# High memory process
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=high-memory-process' -p 'node_name=<node_name>'

# Zombie process
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=zombie-process' -p 'node_name=<node_name>'

# HA resource status
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=ha-resource-status' -p 'node_name=<node_name>'
```

### Strategies Requiring `env`

```bash
# Port check
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port>"}' -p 'node_name=<node_name>'

# Network connectivity test
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=network-connectivity-test' \
  -p 'env={"TARGET_IP":"<target_ip>"}' -p 'node_name=<node_name>'

# Process basic info
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"java"}' -p 'node_name=<node_name>'

# Process file descriptor / jstack thread dump
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=process-file-descriptor' \
  -p 'env={"PID":"<pid>"}' -p 'node_name=<node_name>'

# Disk SMART info
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=disk-smart-info' \
  -p 'env={"DISK_DEVICE":"/dev/sda"}' -p 'node_name=<node_name>'

# Network adapter config
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' -p 'strategy_name=network-adapter-config' \
  -p 'env={"NETWORK_ADAPTER_NAME":"<nic>"}' -p 'node_name=<node_name>'
```

> On Windows PowerShell, replace `"` with `"""` inside `env` values, e.g. `-p 'env={"""PID""":"""123"""}'`.

## Log Data Collection

```bash
# Collect alarm log data (standard time format)
python3 scripts/lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=2026/06/11 16:00:32 GMT+08:00' \
  -p 'log_directory=/var/log/hadoop/hdfs' \
  -p 'log_file_name=hadoop-hdfs-datanode.log' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local'

# Collect alarm log data (non-standard time format, with time_pattern)
python3 scripts/lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=2026/07/07 20:54:00 GMT+08:00' \
  -p 'log_directory=/var/log/Bigdata/omm/oms/pms' \
  -p 'log_file_name=pms*.log' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local' \
  -p 'time_pattern=^\[([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})||ymdHMS'
```

## MRS Manager Proxy (GET)

```bash
# Query audit dump config
python3 scripts/lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/audits/config'

# Query audit logs (returns totalCount)
python3 scripts/lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/audits?limit=1'
```

> `target_url` MUST NOT start with `/`. GET only (PUT not yet supported). Requires Agent >= 1.0.5.

## Quick Reference Table

| API | Required Params | Purpose |
|-----|-----------------|---------|
| `query_alarm_skill` | `cluster_id`, `alarm_sequence_id` | Query alarm diagnosis skill content |
| `query-alarm-info` | `cluster_id`, `alarmSequenceId` | Query alarm info |
| `query-node-ip` | `cluster_id`, `nodeName` | Resolve node name to IP |
| `query-management-node-info` | `cluster_id` | Query primary/standby node names |
| `collect_alarm_node_res_data` | `cluster_id`, `strategy_name` | Collect node resource data |
| `collect_alarm_log_data` | `cluster_id`, `alarm_time`, `log_directory`, `log_file_name`, `keywords`, `log_type` | Collect alarm log data |
| `access_manager_get` | `cluster_id`, `target_url` | Proxy MRS Manager GET API |
| `get_token` | (auto) | Obtain token (built-in, auto-called) |

## Variable Substitution

| Variable | Description | Example |
|----------|-------------|---------|
| `<cluster_id>` | MRS cluster ID | `b46a9c34-c2b4-4208-9a3b-89581764bff6` |
| `<alarm_serial_no>` | Alarm sequence ID | `1` |
| `<node_name>` | Alarm node host name | `8-5-225-5` |
| `<target_ip>` | Target node IP | `8.5.225.6` |
| `<port>` | Port number | `22` |
| `<pid>` | Process ID | `392208` |
| `<nic>` | Network adapter name | `eth0` |
| `<alarm_time>` | Alarm occurrence time | `2026/06/11 16:00:32 GMT+08:00` |
