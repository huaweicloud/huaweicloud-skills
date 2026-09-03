# Data Collection

> This file is loaded in SKILL.md step 1. It collects basic data including node status, processes, ports, HA, resources, alarms, and framework logs.

## 1.1 Load Component Config

Load `components/<service_name>.md` to obtain process names, ports, log paths, and other information.

If the component config file does not exist, inform the user:
> The config file for component `<service_name>` does not exist. Please copy `components/_template.md` and rename it to `<service_name>.md`, fill in the component information, and retry.

## 1.2 Query OMS Active/Standby Nodes

```bash
python lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

Record `oms_active_node` (Active OMS node name).

> If the user did not provide node_name, perform subsequent collection on both OMS Active and Standby nodes.

## 1.3 Collect Process Status

Execute for each process name listed in the component config file:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Record: whether the process exists, process status (R/S/D/Z/T), process count.

## 1.4 Collect Port Status

Execute for each port listed in the component config file:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Record: whether the port is listening, listening process.

## 1.5 Collect HA Resource Status

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

Record: HA resource name, ResStatus, ResHAStatus.

## 1.6 Collect Node Resources

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

## 1.7 Query Alarms

```bash
# Query alarms via access_manager_get (if available)
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/alarms'
```

> **Known limitation**: `access_manager_get` returns 500 on some versions. Alternative: detect alarms via Controller logs.

> **The alarm ID list is consistent with `fault_layer/service_fault.md` step 1.3. When adding new alarm IDs, update both places synchronously.**

```bash
# Alternative: Detect alarm keywords via Controller logs
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","alarm","12006","12007","14000","16004","18000","18021","25000","25500","27001","raise","healthState","BAD","unavailable"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

Alarm matching:

| Log Keyword | Alarm Type |
|-------------|------------|
| 12006 / NodeAgent / agent abnormal | NodeAgent process abnormal |
| 12007 / process / PID / process abnormal | Process fault |
| Specific service unavailable alarm ID + service name | Service unavailable alarm (alarm ID mapping see `fault_layer/service_fault.md` step 1.3) |
| service unavailable / healthState=BAD / raise alarm | Service unavailable (no specific alarm ID) |
| No alarm keywords | No active alarms |

## 1.8 Collect Framework Operation Logs (for scenario identification)

> **Note**: Only query framework-layer logs, not component's own logs. Component logs (e.g., krb5kdc.log, gaussdb.log) have varying formats and are not used for scenario identification.

```bash
# Controller operation logs (framework layer, records operation dispatch)
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","install","reinstall","start","stop","scale","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'

# NodeAgent script logs (framework layer, records operation execution)
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","install","reinstall","start","stop","scale","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Target node name |
| <oms_active_node> | Step 1.2 | OMS Active node name |
| <alarm_time> | Input parameter | Time basis for log collection |
| <process_name> | Component config file | components/<service_name>.md |
| <port_number> | Component config file | components/<service_name>.md |
