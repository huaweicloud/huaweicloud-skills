# Scale Out Scenario Diagnosis

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: New Node Environment Check
  │
  ├─ Step 2: Installation and Distribution Check
  │
  ├─ Step 3: Data Synchronization Check
  │
  ├─ Step 4: Cluster Configuration Update Check
  │
  └─ Step 5: Post-Scale-Out Verification
```

## Step 1: New Node Environment Check

**Goal**: Confirm that the new node's basic environment meets the scale-out requirements (network connectivity, disk space, OS compatibility, dependent software).

### 1.1 New Node Network Connectivity

Check network connectivity between the new node, the OMS master node, and existing cluster nodes:

```bash
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<oms_active_node>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

> **Note**: The `port` parameter uses the dependency service port listed in the `dependency relationship` table of the component config file, or the component's own first port.

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Connection timeout | Firewall not opened or security group not configured | Check firewall rules and security group policies |
| Cannot route | New node not added to the correct network segment/VPC | Check network configuration and routing table |
| SSH unreachable | New node not registered to OMS or SSH key not configured | Register the node on OMS, configure SSH trust |
| DNS resolution failed | New node hostname not registered in DNS | Check /etc/hosts and DNS configuration |

### 1.2 New Node Disk Space

Confirm sufficient disk space on each mount point of the new node (installation directory, data directory, log directory):

```bash
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json
```

**Abnormal judgment**:

| Mount Point | Threshold | Conclusion |
|-------------|-----------|------------|
| /opt (installation directory) | Usage ≥ 85% | Insufficient space, need to clean up or expand disk |
| /srv (data directory) | Usage ≥ 85% | Insufficient space, need to clean up or expand disk |
| /var/log (log directory) | Usage ≥ 85% | Insufficient space, need to clean up |

### 1.3 New Node System Load and Memory

```bash
# Memory check
python manager_api_client.py -a get_host_detail \
  -p 'hostname=<node_name>' --json

# System load check
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<node_name>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' --json
```

### 1.4 New Node Port Conflict Check

Confirm that the ports required by the component on the new node are not occupied (there should be no residual processes or listening ports before scale-out):

```bash
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each port listed in the component config file. If the port is already occupied, there is a residual process on the new node or a conflict with another service.

### 1.5 New Node Residual Process Check

Confirm that there are no residual processes of the same-named component on the new node:

```bash
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name listed in the component config file. Before scale-out, no process of this component should exist on the new node.

---

## Step 2: Installation and Distribution Check

**Goal**: Confirm that the installation package was correctly distributed to the new node and configuration files were correctly generated.

### 2.1 Installation Package Distribution Check

Check the Controller logs for errors related to distributing the installation package to the new node:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Package not found | Installation package not prepared or path error | Check the packages directory on OMS, confirm the installation package is complete |
| scp/ssh failed | SSH trust not configured or network unreachable | Configure SSH trust from OMS to the new node |
| Extract failed | Insufficient disk space or corrupted package | Clean up disk, verify SHA256 |
| Permission denied | Distribution directory permission abnormal | Check /opt/huawei/Bigdata/packages permissions |
| Disk space insufficient | New node disk full | Clean up disk or expand disk |

### 2.2 Configuration File Generation Check

Check the NodeAgent script logs for configuration generation related errors:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Also check whether the configuration files in the component instance directory were correctly generated:
- Check path: `$BIGDATA_HOME/FusionInsight_Current/<instance_index>_<role>/etc/`
- Check file: whether configurations.xml exists and its content is complete

---

## Step 3: Data Synchronization Check

**Goal**: Confirm that the new node data synchronization is complete (DBService active/standby replication, HDFS metadata synchronization, HA relationship establishment).

### 3.1 DBService Data Synchronization Check

For components that depend on DBService, check whether data synchronization (active/standby replication) completed normally:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=DBService:DBService:DBServer' \
  -p 'min_log_level=WARN' \
  -p 'key_word=replication' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| pg_basebackup failed | Large primary node data volume or insufficient network bandwidth | Check network bandwidth, use incremental synchronization if necessary |
| replication timeout | Synchronization timed out | Check primary node load and network, adjust wal_sender_timeout |
| standby refuse connection | New node IP not authorized in primary node pg_hba.conf | Check primary node pg_hba.conf, add the new node IP |
| WAL archive missing | WAL archive missing causing incremental synchronization failure | Check WAL archive configuration, do full resynchronization if necessary |

### 3.2 HA Relationship Establishment Check

Check whether the HA configuration correctly established the new node's active/standby relationship:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=join' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

Also check whether the HA resource status is normal:

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

### 3.3 HDFS Metadata Synchronization Check (if applicable)

For HDFS-related components, check the NameNode metadata synchronization logs:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=HDFS:HDFS:NameNode' \
  -p 'min_log_level=WARN' \
  -p 'key_word=bootstrap' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

---

## Step 4: Cluster Configuration Update Check

**Goal**: Confirm that cluster-level configuration is correctly updated after scale-out (krb5.conf, HA configuration, service registration).

### 4.1 Controller Configuration Update Log

Check the Controller logs for cluster configuration update related records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=scale_out' --json
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Config update failed | Cluster configuration update failed | Check Controller configuration generation logs, fix the parameters |
| Service register failed | New instance failed to register to the cluster | Check instance registration status in the OMS database |
| krb5.conf update failed | Kerberos configuration update failed | Check KDC connectivity and whether the principal has been created |
| HA config sync failed | HA configuration failed to sync to the new node | Check HA configuration file distribution logs |

### 4.2 New Node Configuration File Check

Check whether the key configuration files on the new node were correctly updated:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 4.3 Service Registration Status Check

Confirm that the new instance has been correctly registered in the cluster:

```bash
python manager_api_client.py -a get_oms_info --json
```

Check whether the returned result contains the instance information of the new node `<node_name>`.

---

## Step 5: Post-Scale-Out Verification

**Goal**: Confirm that after scale-out completes, the new instance runs normally, HA status is normal, and there are no data consistency issues.

### 5.1 New Instance Process and Port Verification

Confirm that the component process on the new node has started and the ports are listening normally:

```bash
# Process check
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json

# Port check
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Execute this check for each process name and port number listed in the component config file. After scale-out, the process on the new node should exist and the ports should be listening.

### 5.2 HA Status Verification

Confirm that the new node has correctly joined the HA cluster and is in the expected role (Active or Standby):

```bash
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**Verification criteria**:

| Check Item | Expected Result | Abnormality Handling |
|------------|-----------------|----------------------|
| HA resource status | New node resource status is Normal | Check HA logs, confirm whether resources need to be started manually |
| Active/standby relationship | New node role is Standby (or Active as planned) | Check HA configuration, confirm the active/standby relationship is correct |
| Data synchronization status | Synchronization status is Data syncing or synced | Wait for synchronization to complete; if not synced for a long time, investigate |

### 5.3 Data Consistency Verification

Check the new node component logs for data inconsistency related errors:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=consistency' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

Log paths and file names refer to the `log path` table in the component config file; execute the check for each role.

### 5.4 OMM Process Tree Verification

Confirm that the component process tree structure on the new node is complete:

```bash
# manager mode uses get_host_process instead of omm-process-tree
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

### 5.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Scale Out` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `get_host_process`
- Log check → `browse_log` / `start_log_search`
- HA status → `get_instances`
- Network connectivity → `check_remote`

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| New node network unreachable | network-connectivity-test shows connection timeout | Check firewall, security group, routing, and SSH trust |
| New node disk space insufficient | disk-space check shows ≥85% | Clean up disk space or expand disk |
| Installation package distribution failed | Controller logs have scp/ssh failed or Package not found | Configure SSH trust, check the packages directory |
| Configuration generation failed | Script logs have genConfig ERROR | Check configuration templates and scale-out parameters |
| Data synchronization timeout | DBService logs have replication timeout or basebackup failed | Check network bandwidth and primary node load, do full resynchronization if necessary |
| HA join failed | HA logs have join/add ERROR, abnormal ha-resource-status | Check HA configuration file and network, fix the HA relationship manually |
| New node port conflict | port-check shows the port is already occupied | Clean up residual processes or investigate the conflicting service |
| Kerberos configuration not updated | krb5.conf update failed | Check KDC connectivity, create principal for the new node |
| Service registration failed | query-management-node-info has no new node instance | Check the registration status in the OMS database, manually retry registration |
| Data inconsistency | Component logs have consistency/corrupt ERROR | Investigate the data synchronization chain, do full resynchronization if necessary |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Scale-out target new node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <port> | Component config file | Component listening port |
| <process_name> | Component config file | Component process name |
| <log_directory> | Component config file | Component log directory |
| <log_file_name> | Component config file | Component log file name |
| <instance_index> | Component config file | e.g., 1_4, 1_5 |
| <role> | Component config file | e.g., DBServer, DBroker |
