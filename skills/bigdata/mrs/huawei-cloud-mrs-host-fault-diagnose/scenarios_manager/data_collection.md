# Basic Information Collection

> This file is loaded in SKILL.md step 1. It collects basic data including node status, processes, ports, HA, resources, alarms, and framework logs.

## 1.1 Load Component Config

Load `components/<service_name>.md` to obtain process names, ports, log paths, and other information.

If the component config file does not exist, inform the user:
> The config file for component `<service_name>` does not exist. Please copy `components/_template.md` and rename it to `<service_name>.md`, fill in the component information, and retry.

## 1.2 Query OMS Active/Standby Nodes

```bash
python manager_api_client.py -a get_oms_info --json
```

Record `oms_active_node` (Active OMS node name).

> If the user has not provided node_name, perform the subsequent collection on both the OMS Active and Standby nodes.

## 1.3 Collect Process Status

For each process name listed in the component config file:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Record: whether the process exists, process state (R/S/D/Z/T), and process count.

## 1.4 Collect Port Status

For each port listed in the component config file:

```bash
# No independent port check API in manager mode
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Record: whether the port is listening and which process is listening on it.

## 1.5 Collect HA Resource Status

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

Record: HA resource name, ResStatus, ResHAStatus.

## 1.6 Collect Node Resources

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

## 1.7 Query Alarms

```bash
# Query alarms through the Manager API
python manager_api_client.py -a get_alarms --json
```

> **Known limitation**: `access_manager_get` returns 500 in some versions. Alternative: detect alarms through Controller logs.

> **The alarm number list must stay consistent with step 1.3 of `fault_layer_manager/service_fault.md`; when adding new alarm numbers, modify both locations in sync.**

```bash
# Alternative: detect alarm keywords through Controller logs
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Alarm matching:

| Log Keyword | Alarm Type |
|-------------|------------|
| 12006 / NodeAgent / agent abnormal | NodeAgent process abnormal |
| 12007 / process / PID / process abnormal | Process fault |
| Specific service-unavailable alarm number + service name | Service unavailable alarm (alarm number mapping see step 1.3 of `../fault_layer_manager/service_fault.md`) |
| service unavailable / healthState=BAD / raise alarm | Service unavailable (no specific alarm number) |
| No alarm keyword | No active alarm |

## 1.8 Collect Framework Operation Logs (auxiliary scenario identification)

> **Note**: Only query framework-layer logs, not the component's own logs. Component logs (such as krb5kdc.log, gaussdb.log) vary in format and are not used for scenario identification.

```bash
# Controller operation log (framework layer, records operation dispatch)
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json

# NodeAgent script log (framework layer, records operation execution)
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Target node name |
| <oms_active_node> | Step 1.2 | OMS Active node name |
| <alarm_time> | Input parameter | Time baseline for log collection |
| <process_name> | Component config file | components/<service_name>.md |
| <port> | Component config file | components/<service_name>.md |
