# Reinstall Host Scenario Diagnosis

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> This scenario covers the reinstallation and data restoration of all component instances on the host after the host operating system has been reinstalled.

> **Difference from component reinstall**:
> - reinstall: Reinstall a single component instance on a normally running host
> - reinstall_host: The entire operating system is reinstalled, so all component instances on the host must be reinstalled and their data restored

## Diagnosis Flow

```
Step 1: Host Basic Environment Check — Network/SSH/Disk/User/Timezone
  │
  ├─ Step 2: NodeAgent Reinstall Check — Whether NodeAgent was reinstalled and runs normally
  │
  ├─ Step 3: Component Instance Reinstall Check — Reinstall and data restoration of each component instance
  │
  ├─ Step 4: Data Restore Verification — Whether each component data directory was correctly restored
  │
  └─ Step 5: Cluster Integration Verification — Overall status after the host rejoins the cluster
```

## Step 1: Host Basic Environment Check

**Goal**: Confirm that the basic environment is correctly configured after the host operating system reinstall

### 1.1 Network Configuration Check

```bash
# manager mode uses get_host_detail instead of network-interface-info
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Key observation points**:
- Whether the IP address is consistent with before the reinstall
- Whether the network interface name is correct
- Whether the routing configuration is normal

### 1.2 SSH Trust Check

SSH trust may be lost after reinstall; check the SSH connection from the omm user to the OMS master node:

```bash
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<oms_active_node_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

> **Note**: ssh-check verifies SSH trust by executing `ssh <TARGET_IP> "echo ''"`. If empty data is returned or code!=200, SSH trust is abnormal.

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| SSH connection refused | SSH key not restored or sshd not started | Restore omm user SSH key, start sshd service |
| Host key verification failed | known_hosts mismatch | Clear old host fingerprints from known_hosts |
| Permission denied | Incorrect SSH key permissions | Fix permissions: chmod 700 ~/.ssh, chmod 600 ~/.ssh/id_rsa |

### 1.3 Disk Space Check

```bash
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Key observation points**:
- Whether the system disk has enough space to install components
- Whether the data disk partition is correct (/srv/BigData/)
- Whether each data directory mount is normal

### 1.4 System Resource Check

```bash
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' --json
```

```bash
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

### 1.5 System Configuration Check

```bash
# manager mode uses get_host_detail instead of dns-check
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

```bash
# manager mode uses get_host_detail instead of systemd-detect-virt
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| omm user does not exist | omm user not created after OS reinstall | Re-add the node through Manager or create it manually |
| Incorrect timezone | Timezone not configured after reinstall | Set correct timezone: timedatectl set-timezone Asia/Shanghai |
| DNS resolution abnormal | /etc/resolv.conf not correctly configured | Restore DNS configuration |
| hostname mismatch | hostname inconsistent with cluster registration after reinstall | Modify hostname to be consistent with cluster registration |

---

## Step 2: NodeAgent Reinstall Check

**Goal**: Confirm whether NodeAgent was correctly reinstalled and runs normally

### 2.1 NodeAgent Process Check

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

**Judgment**:

| Result | Conclusion | Next Step |
|--------|------------|-----------|
| Process exists and running | NodeAgent reinstall succeeded | Step 3 |
| Process does not exist | NodeAgent not installed or start failed | Check NodeAgent installation log |
| API call failed | Node unreachable or Agent not started | Re-check basic environment in Step 1 |

### 2.2 NodeAgent Installation Log Check

Check the Controller logs for NodeAgent installation related records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<node_name>' --json
```

### 2.3 NodeAgent Start/Stop Log Check

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=ERROR' --json
```

---

## Step 3: Component Instance Reinstall Check

**Goal**: Confirm whether each component instance on the host was correctly reinstalled

### 3.1 Query Component Instances on the Host

```bash
python manager_api_client.py -a get_cluster_services \
  -p 'cluster_id=<cluster_id>' --json
```

> **Note**: This API requires Manager permission; if the call fails, troubleshoot through the Controller logs.

### 3.2 Controller Installation Operation Log

Check the Controller logs for the component installation records for this node:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<node_name>' --json
```

### 3.3 NodeAgent Script Execution Log

Check the NodeAgent script logs for component installation execution records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=install' --json
```

### 3.4 Check Processes of Each Component

Based on the component list that should exist on this host, check the processes one by one:

```bash
# manager mode uses get_host_process instead of omm-process-tree
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

**Key observation points**:
- Which component processes should be present on this host (obtained from the cluster configuration)
- Which processes exist and which are missing
- Whether the process tree structure is complete

### 3.5 Port Check

Check whether each component port on this host is listening:

```bash
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each component port on this host.

---

## Step 4: Data Restore Verification

**Goal**: Confirm whether each component data directory was correctly restored

### 4.1 Data Directory Check

```bash
# manager mode uses get_host_detail instead of oms_core_dir
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Key observation points**:
- Whether the BIGDATA_HOME and BIGDATA_DATA_HOME paths are correct
- Whether the data directory exists and has data

### 4.2 Check Logs of Each Component

For each component on this host, check its runtime logs for data restore related errors:

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

### 4.3 HA Status Check (HA components)

For the HA components on this host, check the HA resource status:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**Key observation points**:
- Whether the HA component correctly rebuilt the active/standby relationship
- Whether the host's HA role matches expectations (Active/Standby)

---

## Step 5: Cluster Integration Verification

**Goal**: Confirm that the overall status is normal after the host rejoins the cluster

### 5.1 Node Reachability Verification

Ping the reinstalled host from the OMS master node:

```bash
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<node_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

### 5.2 Alarm Status Check

Check whether there are any unresolved alarms on this host:

```bash
python manager_api_client.py -a get_alarms --json
```

**Key observation points**:
- Whether there is a 12006 (NodeAgent abnormal) alarm
- Whether there is a 12007 (process fault) alarm
- Whether the service unavailable alarms for each component have been recovered

### 5.3 Component Health Status

```bash
python manager_api_client.py -a get_cluster_services \
  -p 'cluster_id=<cluster_id>' --json
```

Check whether the overall status of each component service is Good.

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| SSH trust not restored | SSH connection refused, omm user SSH key missing | Restore omm user SSH key pair, configure authorized_keys |
| omm user not created | omm user does not exist after OS reinstall, all installations fail | Re-add the node through Manager or create the omm user manually |
| Data directory not mounted | Disk space check shows the data disk not mounted to /srv/BigData | Mount the data disk and restore the fstab configuration |
| NodeAgent installation failed | Controller logs have NodeAgent install fail | Check installation package integrity, network connectivity, and system dependencies |
| Component data not restored | Component logs have corrupt/inconsistent/restore fail | Restore data from backup or re-initialize |
| HA active/standby relationship abnormal | HA resource status abnormal, active/standby relationship not rebuilt | Reconfigure the HA active/standby relationship, refer to each component config file |
| hostname inconsistent | Node shows abnormal on the Manager page | Modify hostname to be consistent with the cluster registration name |
| Firewall not disabled | Some component processes exist but ports are unreachable | Disable the firewall or open the required ports |
| Time not synchronized | NTP not configured, node time not synchronized with cluster | Configure NTP and wait for time synchronization |
| Dependent components not installed | Component logs have dependency service connection failures | Install components in dependency order (LdapServer→KrbServer→DBService→...) |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <node_name> | Input parameter | Reinstall host name |
| <node_ip> | Obtained via query-node-ip | Reinstall host IP |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <oms_active_node_ip> | Obtained via query-node-ip | OMS master node IP |
| <alarm_time> | Input parameter | Operation time |
| <port> | Component config file | Port of each component |
| <component_log_directory> | Component config file | Log path of each component |
| <component_log_file_name> | Component config file | Log file name pattern of each component |
