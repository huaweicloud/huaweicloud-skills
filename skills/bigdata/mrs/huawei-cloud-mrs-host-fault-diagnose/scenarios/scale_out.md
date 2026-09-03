# Scale Out Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: New Node Environment Check
  │
  ├─ Step 2: Installation Distribution Check
  │
  ├─ Step 3: Data Sync Check
  │
  ├─ Step 4: Cluster Configuration Update Check
  │
  └─ Step 5: Post-Scale-Out Verification
```

## Step 1: New Node Environment Check

**Goal**: Confirm that the new node's basic environment meets scale-out requirements (network connectivity, disk space, OS compatibility, dependency software).

### 1.1 New Node Network Connectivity

Check network connectivity between the new node and the OMS master node and existing cluster nodes:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-connectivity-test' \
  -p 'env={"target_node":"<oms_active_node>","port":"<dependency_port>"}' \
  -p 'node_name=<node_name>'
```

> **Note**: The `port` parameter uses the dependency service port from the component config file's `dependency` table, or the component's own first port.

**Common Issues**:

| Abnormality | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Connection timeout | Firewall not open or security group not configured | Check firewall rules and security group policies |
| Unroutable | New node not in correct subnet/VPC | Check network configuration and routing table |
| SSH unreachable | New node not registered to OMS or SSH key not configured | Register node on OMS, configure SSH mutual trust |
| DNS resolution failed | New node hostname not registered in DNS | Check /etc/hosts and DNS configuration |

### 1.2 New Node Disk Space

Confirm sufficient disk space on each mount point of the new node (installation directory, data directory, log directory):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<node_name>'
```

**Abnormality Criteria**:

| Mount Point | Threshold | Conclusion |
|-------------|-----------|------------|
| /opt (installation directory) | Usage ≥ 85% | Insufficient space, need cleanup or disk expansion |
| /srv (data directory) | Usage ≥ 85% | Insufficient space, need cleanup or disk expansion |
| /var/log (log directory) | Usage ≥ 85% | Insufficient space, need cleanup |

### 1.3 New Node System Load and Memory

```bash
# Memory check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=memory-usage' \
  -p 'node_name=<node_name>'

# System load check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

### 1.4 New Node Port Conflict Check

Confirm that the ports required by the component on the new node are not occupied (there should be no residual processes or port listening before scale-out):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each port listed in the component config file. If the port is already occupied, it means there are residual processes on the new node or a conflict with another service.

### 1.5 New Node Residual Process Check

Confirm there are no residual processes of the same-named component on the new node:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name listed in the component config file. There should be no processes of this component on the new node before scale-out.

---

## Step 2: Installation Distribution Check

**Goal**: Confirm that the installation package is correctly distributed to the new node and configuration files are correctly generated.

### 2.1 Installation Package Distribution Check

Check the Controller logs for errors related to installation package distribution to the new node:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","scale_out","distribute","package","scp","extract","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Package not found | Installation package not prepared or path error | Check packages directory on OMS, confirm package integrity |
| scp/ssh failed | SSH mutual trust not configured or network unreachable | Configure SSH mutual trust from OMS to new node |
| Extract failed | Insufficient disk space or corrupted package | Clean up disk, verify SHA256 |
| Permission denied | Distribution directory permission abnormal | Check /opt/huawei/Bigdata/packages permissions |
| Disk space insufficient | New node disk full | Clean up disk or expand disk |

### 2.2 Configuration File Generation Check

Check the NodeAgent script logs for configuration generation related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","config","genConfig","scale_out","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Also check whether configuration files have been correctly generated in the component instance directory:
- Check path: `$BIGDATA_HOME/FusionInsight_Current/<instance_number>_<role>/etc/`
- Check file: whether configurations.xml exists and content is complete

---

## Step 3: Data Sync Check

**Goal**: Confirm that new node data sync is complete (DBService primary/standby replication, HDFS metadata sync, HA relationship establishment).

### 3.1 DBService Data Sync Check

For components that depend on DBService, check whether data sync (primary/standby replication) has completed normally:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/DB' \
  -p 'log_file_name=gaussdb-*.log*' \
  -p 'keywords=["replication","basebackup","standby","sync","ERROR","fail","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| pg_basebackup failed | Large data volume on primary node or insufficient network bandwidth | Check network bandwidth, use incremental sync if necessary |
| replication timeout | Sync timed out | Check primary node load and network, adjust wal_sender_timeout |
| standby refuse connection | Primary node pg_hba.conf not authorized | Check primary node pg_hba.conf, add new node IP |
| WAL archive missing | WAL archive missing causing incremental sync failure | Check WAL archive configuration, use full re-sync if necessary |

### 3.2 HA Relationship Establishment Check

Check whether HA configuration has correctly established the new node's active/standby relationship:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/dbservice/ha' \
  -p 'log_file_name=ha.log*' \
  -p 'keywords=["join","add","standby","configure","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Also check whether HA resource status is normal:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

### 3.3 HDFS Metadata Sync Check (if applicable)

For HDFS-related components, check the NameNode metadata sync logs:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/hdfs/nn' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["bootstrap","namenode","standby","sync","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

---

## Step 4: Cluster Configuration Update Check

**Goal**: Confirm that cluster-level configuration is correctly updated after scale-out (krb5.conf, HA configuration, service registration).

### 4.1 Controller Configuration Update Logs

Check the Controller logs for cluster configuration update related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["scale_out","config","update","register","krb5","HA","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Config update failed | Cluster configuration update failed | Check Controller configuration generation logs, fix parameters |
| Service register failed | New instance registration to cluster failed | Check instance registration status in OMS database |
| krb5.conf update failed | Kerberos configuration update failed | Check KDC connectivity and whether principal has been created |
| HA config sync failed | HA configuration sync to new node failed | Check HA configuration file distribution logs |

### 4.2 New Node Configuration File Check

Check whether key configuration files on the new node have been correctly updated:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","scale_out","config","krb5","HA","register","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 4.3 Service Registration Status Check

Confirm that the new instance has been correctly registered in the cluster:

```bash
python lakewatch_api_client.py -a query-management-node-info \
  -p 'cluster_id=<cluster_id>'
```

Check whether the returned results include instance information for the new node `<node_name>`.

---

## Step 5: Post-Scale-Out Verification

**Goal**: Confirm that after scale-out is complete, the new instance is running normally, HA status is normal, and there are no data consistency issues.

### 5.1 New Instance Process and Port Verification

Confirm that component processes on the new node have started and ports are listening normally:

```bash
# Process check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'

# Port check
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

Execute this check for each process name and port listed in the component config file. After scale-out, processes should exist and ports should be listening on the new node.

### 5.2 HA Status Verification

Confirm that the new node has correctly joined the HA cluster and is in the expected role (Active or Standby):

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Verification Criteria**:

| Check Item | Expected Result | Abnormal Handling |
|------------|-----------------|-------------------|
| HA resource status | New node resource status is Normal | Check HA logs, confirm whether manual resource start is needed |
| Active/standby relationship | New node role is Standby (or Active as planned) | Check HA configuration, confirm active/standby relationship is correct |
| Data sync status | Sync status is Data syncing or synced | Wait for sync to complete; if not synced for a long time, investigate |

### 5.3 Data Consistency Verification

Check the new node component logs for data inconsistency related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<log_directory>' \
  -p 'log_file_name=<log_file_name>' \
  -p 'keywords=["consistency","inconsistent","corrupt","ERROR","FATAL","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Refer to the `log path` table in the component config file and execute the check for each role.

### 5.4 OMM Process Tree Verification

Confirm that the component process tree structure on the new node is complete:

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=omm-process-tree' \
  -p 'node_name=<node_name>'
```

### 5.5 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Scale Out` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)
- Network connectivity → `collect_alarm_node_res_data` (network-connectivity-test)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| New node network unreachable | network-connectivity-test shows connection timeout | Check firewall, security groups, routing, and SSH mutual trust |
| New node insufficient disk space | disk-space check shows ≥85% | Clean up disk space or expand disk |
| Installation package distribution failed | Controller logs have scp/ssh failed or Package not found | Configure SSH mutual trust, check packages directory |
| Configuration generation failed | Script logs have genConfig ERROR | Check configuration template and scale-out parameters |
| Data sync timeout | DBService logs have replication timeout or basebackup failed | Check network bandwidth and primary node load, use full re-sync if necessary |
| HA join failed | HA logs have join/add ERROR, ha-resource-status abnormal | Check HA configuration file and network, manually fix HA relationship |
| New node port conflict | port-check shows port already occupied | Clean up residual processes or investigate port-conflicting service |
| Kerberos configuration not updated | krb5.conf update failed | Check KDC connectivity, create principal for new node |
| Service registration failed | query-management-node-info does not include new node instance | Check OMS database registration status, manually retry registration |
| Data inconsistency | Component logs have consistency/corrupt ERROR | Investigate data sync chain, re-sync full data if necessary |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Scale-out target new node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <port_number> | Component config file | Component listening port |
| <process_name> | Component config file | Component process name |
| <log_directory> | Component config file | Component log directory |
| <log_file_name> | Component config file | Component log file name |
| <instance_number> | Component config file | e.g., 1_4, 1_5 |
| <role> | Component config file | e.g., DBServer, DBroker |
