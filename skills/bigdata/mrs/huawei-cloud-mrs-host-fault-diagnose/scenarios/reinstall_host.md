# Reinstall Host Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> This scenario targets the reinstallation and data recovery of all component instances on a host after the host OS has been reinstalled.

> **Difference from component reinstall (reinstall)**:
> - reinstall: Reinstall a specific component instance on a normally running host
> - reinstall_host: The entire OS is reinstalled; all component instances on the host need to be reinstalled and data recovered

## Diagnosis Flow

```
Step 1: Host Basic Environment Check — Network/SSH/Disk/User/Timezone
  │
  ├─ Step 2: NodeAgent Reinstall Check — Whether NodeAgent is reinstalled and running normally
  │
  ├─ Step 3: Component Instance Reinstall Check — Reinstallation and data recovery of each component instance
  │
  ├─ Step 4: Data Recovery Verification — Whether each component's data directory is correctly recovered
  │
  └─ Step 5: Cluster Integration Verification — Overall status after host rejoins cluster
```

## Step 1: Host Basic Environment Check

**Goal**: Confirm whether the basic environment is correctly configured after host OS reinstall

### 1.1 Network Configuration Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-interface-info' \
  -p 'node_name=<node_name>'
```

**Key Observations**:
- Whether the IP address is consistent with before reinstall
- Whether the network interface name is correct
- Whether the routing configuration is normal

### 1.2 SSH Mutual Trust Check

SSH mutual trust may be lost after reinstall; check the SSH connection from omm user to OMS master node:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ssh-check' \
  -p 'env={"TARGET_IP":"<oms_active_node_ip>"}' \
  -p 'node_name=<node_name>'
```

> **Note**: ssh-check verifies SSH mutual trust by executing `ssh <TARGET_IP> "echo ''"`. If it returns empty data or code!=200, SSH mutual trust is abnormal.

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| SSH connection refused | SSH key not restored or sshd not started | Restore omm user SSH keys, start sshd service |
| Host key verification failed | known_hosts mismatch | Clean old host fingerprints from known_hosts |
| Permission denied | SSH key permissions incorrect | Fix permissions: chmod 700 ~/.ssh, chmod 600 ~/.ssh/id_rsa |

### 1.3 Disk Space Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

**Key Observations**:
- Whether the system disk has enough space for component installation
- Whether the data disk partition is correct (/srv/BigData/)
- Whether each data directory is mounted normally

### 1.4 System Resource Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=memory-usage' \
  -p 'node_name=<node_name>'
```

### 1.5 System Configuration Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=dns-check' \
  -p 'node_name=<node_name>'
```

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=systemd-detect-virt' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| omm user does not exist | omm user not created after OS reinstall | Re-add node via Manager or manually create omm user |
| Timezone incorrect | Timezone not configured after reinstall | Set correct timezone: timedatectl set-timezone Asia/Shanghai |
| DNS resolution abnormal | /etc/resolv.conf not correctly configured | Restore DNS configuration |
| hostname mismatch | hostname after reinstall inconsistent with cluster registration | Change hostname to match cluster registration |

---

## Step 2: NodeAgent Reinstall Check

**Goal**: Confirm whether NodeAgent has been correctly reinstalled and is running normally

### 2.1 NodeAgent Process Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"NodeAgent"}' \
  -p 'node_name=<node_name>'
```

**Evaluation**:

| Result | Conclusion | Next Step |
|--------|------------|-----------|
| Process exists and running | NodeAgent reinstall successful | Step 3 |
| Process does not exist | NodeAgent not installed or start failed | Check NodeAgent installation logs |
| API call failed | Node unreachable or Agent not started | Re-check basic environment in Step 1 |

### 2.2 NodeAgent Installation Log Check

Check the Controller logs for NodeAgent installation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<node_name>","install","NodeAgent","package","distribute","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 2.3 NodeAgent Start/Stop Log Check

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=nodeagent_ctl*' \
  -p 'keywords=["ERROR","Exception","OutOfMemoryError","start","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

---

## Step 3: Component Instance Reinstall Check

**Goal**: Confirm whether each component instance on the host has been correctly reinstalled

### 3.1 Query Component Instances on the Host

```bash
python lakewatch_api_client.py -a manager-access-get \
  -p 'cluster_id=<cluster_id>' \
  -p 'targetUrl=api/v2/clusters/<cluster_id>/hosts/<node_name>/services'
```

> **Note**: This API requires Manager permissions; if it fails, investigate via Controller logs.

### 3.2 Controller Installation Operation Logs

Check the Controller logs for component installation records on this node:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<node_name>","install","package","distribute","config","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 3.3 NodeAgent Script Execution Logs

Check the NodeAgent script logs for component installation execution records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["install","config","genConfig","ERROR","fail","exit","permission"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 3.4 Component Process Check for Each Component

Based on the expected component list on this host, check each process individually:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

**Key Observations**:
- Which component processes should exist on this host (obtained from cluster configuration)
- Which processes exist, which are missing
- Whether the process tree structure is complete

### 3.5 Port Check

Check whether each component's ports on this host are listening:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each component's ports on this host.

---

## Step 4: Data Recovery Verification

**Goal**: Confirm whether each component's data directory has been correctly recovered

### 4.1 Data Directory Check

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=oms_core_dir' \
  -p 'node_name=<node_name>'
```

**Key Observations**:
- Whether BIGDATA_HOME and BIGDATA_DATA_HOME paths are correct
- Whether data directories exist and have data

### 4.2 Component Log Check for Each Component

For each component on this host, check its runtime logs for data recovery related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<component_log_directory>' \
  -p 'log_file_name=<component_log_file_name>' \
  -p 'keywords=["ERROR","Exception","corrupt","inconsistent","restore","recover","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 4.3 HA Status Check (HA components)

For HA components on this host, check HA resource status:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Key Observations**:
- Whether HA components have correctly rebuilt active/standby relationships
- Whether this host's HA role matches expectations (Active/Standby)

---

## Step 5: Cluster Integration Verification

**Goal**: Confirm that the overall status is normal after the host rejoins the cluster

### 5.1 Node Connectivity Verification

Ping the reinstalled host from the OMS master node:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ping-check' \
  -p 'env={"TARGET_IP":"<node_ip>"}' \
  -p 'node_name=<oms_active_node>'
```

### 5.2 Alarm Status Check

Check whether there are unrecovered alarms on this host:

```bash
python lakewatch_api_client.py -a manager-access-get \
  -p 'cluster_id=<cluster_id>' \
  -p 'targetUrl=api/v2/alarms?hostName=<node_name>&limit=50'
```

**Key Observations**:
- Whether there are 12006 (NodeAgent abnormal) alarms
- Whether there are 12007 (process fault) alarms
- Whether each component's service unavailable alarms have recovered

### 5.3 Component Health Status

```bash
python lakewatch_api_client.py -a manager-access-get \
  -p 'cluster_id=<cluster_id>' \
  -p 'targetUrl=api/v2/clusters/<cluster_id>/services'
```

Check whether each component service's overall status is Good.

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| SSH mutual trust not restored | SSH connection refused, omm user SSH key missing | Restore omm user SSH key pair, configure authorized_keys |
| omm user not created | omm user does not exist after OS reinstall, all installations fail | Re-add node via Manager or manually create omm user |
| Data directory not mounted | Disk space check shows data disk not mounted to /srv/BigData | Mount data disk and restore fstab configuration |
| NodeAgent installation failed | Controller logs have NodeAgent install fail | Check installation package integrity, network connectivity, system dependencies |
| Component data not recovered | Component logs have corrupt/inconsistent/restore fail | Recover data from backup or re-initialize |
| HA active/standby relationship abnormal | HA resource status abnormal, active/standby relationship not rebuilt | Reconfigure HA active/standby relationship, refer to each component config file |
| hostname inconsistent | Manager page shows node abnormal | Change hostname to match cluster registration name |
| Firewall not closed | Some component processes exist but ports unreachable | Close firewall or open required ports |
| Time out of sync | NTP not configured, node time out of sync with cluster | Configure NTP and wait for time sync |
| Dependency component not installed | Component logs have dependency service connection failure | Install components in dependency order (LdapServer→KrbServer→DBService→...) |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <node_name> | Input parameter | Reinstalled host name |
| <node_ip> | query-node-ip | Reinstalled host IP |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <oms_active_node_ip> | query-node-ip | OMS master node IP |
| <alarm_time> | Input parameter | Operation time |
| <port_number> | Component config file | Each component's ports |
| <component_log_directory> | Component config file | Each component's log path |
| <component_log_file_name> | Component config file | Each component's log file name pattern |
