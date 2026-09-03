# Scale In Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Scale-In Safety Check
  │  ├─ 1.1 Scaled-In Node Role Confirmation (not Active node)
  │  ├─ 1.2 Data Replica Integrity Check
  │  └─ 1.3 Active Task Check (no in-progress tasks)
  │
  ├─ Step 2: Service Migration Check
  │  ├─ 2.1 HA Active/Standby Switchover Check
  │  ├─ 2.2 Data Redistribution Check
  │  └─ 2.3 Connection Drain Check
  │
  ├─ Step 3: Scale-In Execution Check
  │  ├─ 3.1 Controller Scale-In Command Logs
  │  └─ 3.2 NodeAgent Execution Logs
  │
  └─ Step 4: Post-Scale-In Verification
     ├─ 4.1 Remaining Node Health Status
     ├─ 4.2 Data Integrity Verification
     └─ 4.3 HA Configuration Update Verification
```

## Step 1: Pre-Scale-In Safety Check

**Goal**: Confirm that the scaled-in node is in a safe state for scale-in, and will not cause data loss or service interruption

### 1.1 Scaled-In Node Role Confirmation

Check whether the scaled-in node is the Active node (HA components need active/standby switchover first):

```bash
# Check HA resource status of the scaled-in node
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<node_name>'
```

**Criteria**:

| HA Resource Status | Can Scale In | Handling Suggestion |
|--------------------|--------------|---------------------|
| Standby | Yes | Can proceed with scale-in directly |
| Active | No | Need to perform active/standby switchover first, then scale in |
| Single node (no HA) | Need evaluation | Confirm whether the component supports single-node operation |

> **Note**: If the scaled-in node is the Active node and active/standby switchover was not performed, it will cause service interruption. This is the most common root cause in the scale-in scenario.

### 1.2 Data Replica Integrity Check

Check whether data on the scaled-in node has been synced to remaining nodes, confirming replica count meets requirements:

```bash
# Check scaled-in node process and data status
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<node_name>'
```

Also check NodeAgent script logs for data migration/sync related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","replica","sync","migrate","rebalance","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Common Issues**:

| Log Keyword | Possible Cause | Risk Level |
|-------------|----------------|------------|
| Replica not enough | Insufficient replica count, cannot remove node | High - Data loss risk |
| Sync not complete | Data sync not completed | High - Data inconsistency |
| Rebalance failed | Data rebalance failed | Medium - Need manual retry |
| Under-replicated blocks | Insufficient replicas (HDFS scenario) | High - Need to supplement replicas |

### 1.3 Active Task Check

Check whether there are in-progress tasks in the cluster (e.g., balance, migration); scale-in should wait for tasks to complete:

```bash
# Check Controller logs for active task records
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","running","task","job","balance","migrate","in progress"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Criteria**:

| Controller Logs | Conclusion | Handling Suggestion |
|-----------------|------------|---------------------|
| No active task records | Safe | Can proceed with scale-in |
| Has running/in progress tasks | Not safe | Wait for tasks to complete or manually terminate |
| Has balance/migrate tasks | Not safe | Wait for data balancing to complete |

---

## Step 2: Service Migration Check

**Goal**: Confirm that services on the scaled-in node have been correctly migrated to remaining nodes

### 2.1 HA Active/Standby Switchover Check

Check whether the HA component has correctly completed active/standby switchover (if the scaled-in node was originally Active):

```bash
# Check HA resource status of remaining nodes
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<oms_active_node>'
```

Also check HA logs for switchover records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<ha_log_directory>' \
  -p 'log_file_name=<ha_log_file>' \
  -p 'keywords=["failover","switch","takeover","active","standby","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

> **Tip**: HA log directory and file name are obtained from the `log path` table in the component config file `components/<service_name>.md`.

**Common Issues**:

| HA Log Keyword | Possible Cause | Repair Suggestion |
|----------------|----------------|-------------------|
| Failover timeout | Active/standby switchover timed out | Check network and disk I/O, manually trigger switchover |
| Takeover failed | Takeover failed | Check Standby node data consistency |
| Split-brain | Split-brain | Check heartbeat network, isolate fault node |
| No standby available | No available Standby node | Scale out or promote another node to Standby first |

### 2.2 Data Redistribution Check

Check whether data has been migrated from the scaled-in node to remaining nodes:

```bash
# Check data migration logs on the scaled-in node
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<component_log_directory>' \
  -p 'log_file_name=<component_log_file>' \
  -p 'keywords=["decommission","replicate","rebalance","redistribute","migrate","complete","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Criteria**:

| Data Migration Status | Conclusion |
|-----------------------|------------|
| Decommission complete | Data migration completed, node can be safely removed |
| Decommission in progress | Data migration in progress, need to wait |
| Decommission failed | Data migration failed, need to investigate cause |
| Under-replicated | Insufficient replicas, need to supplement replicas first |

### 2.3 Connection Drain Check

Check whether active connections on the scaled-in node have been drained:

```bash
# Check scaled-in node network connection status
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-connectivity-test' \
  -p 'node_name=<node_name>'
```

Also check port listening status, confirming whether the service has stopped accepting new requests:

```bash
# Check whether component port is still listening
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<node_name>'
```

**Criteria**:

| Port Status | Active Connections | Conclusion |
|------------|-------------------|------------|
| Still listening | Has active connections | Connections not drained, scale-in will interrupt service |
| Still listening | No active connections | Can safely stop service |
| Stopped listening | - | Service has been stopped |

---

## Step 3: Scale-In Execution Check

**Goal**: Confirm that the scale-in command was correctly transmitted from Controller to NodeAgent and executed successfully

### 3.1 Controller Scale-In Command Logs

Check the Controller logs for scale-in operation related records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","scale_in","scalein","decommission","remove","delete","ERROR","failed","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common ERROR Keywords**:

| ERROR Keyword | Meaning | Possible Cause |
|---------------|---------|-----------------|
| Node is active, cannot scale in | Node is Active, scale-in not allowed | Active/standby switchover not performed |
| Replica not enough | Insufficient replica count | Remaining replica count below minimum |
| Decommission failed | Data migration failed | Insufficient disk space or network abnormal |
| Agent timeout | NodeAgent response timed out | NodeAgent stuck or under high load |
| Config update failed | Configuration update failed | HA configuration or cluster configuration update failed |
| Operation rejected | Operation rejected | Node status does not allow scale-in |

### 3.2 NodeAgent Execution Logs

Check the scaled-in node's NodeAgent execution of the scale-in operation:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog' \
  -p 'log_file_name=agent.log*' \
  -p 'keywords=["<service_name>","scale_in","decommission","stop","remove","clean","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Also check the NodeAgent script execution logs:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","decommission","remove","delete","clean","stop","ERROR","fail","exit"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

**Result Mapping**:

| Controller Logs | NodeAgent Logs | Script Logs | Conclusion |
|-----------------|----------------|-------------|------------|
| Has ERROR | — | — | Controller layer fault (e.g., pre-check failed) |
| Normal | Has ERROR | — | NodeAgent layer fault |
| Normal | Normal | Has ERROR | Script execution layer fault (e.g., cleanup failed) |
| Normal | Normal | Normal | Continue with Step 4 verification |

---

## Step 4: Post-Scale-In Verification

**Goal**: Confirm that after scale-in is complete, remaining nodes are running normally, data is intact, and configuration has been updated

### 4.1 Remaining Node Health Status

Check the processes, ports, and resource status of remaining nodes:

```bash
# Check remaining node process status (execute for each remaining node)
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=process-basic-info' \
  -p 'env={"process_name":"<process_name>"}' \
  -p 'node_name=<oms_active_node>'

# Check remaining node ports
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=port-check' \
  -p 'env={"PORT":"<port_number>"}' \
  -p 'node_name=<oms_active_node>'

# Check remaining node resource load
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<oms_active_node>'

python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=disk-space' \
  -p 'node_name=<oms_active_node>'
```

**Abnormality Criteria**:

| Check Item | Threshold | Conclusion |
|------------|-----------|------------|
| Process does not exist | - | Scale-in caused service to stop abnormally |
| Port not listening | - | Service not started normally |
| CPU load ≥ cores × 2 | Remaining node overloaded | Load too high after scale-in, need scale-out |
| Disk usage ≥ 85% | Disk nearly full | Data migration caused increased disk usage |
| Memory usage ≥ 95% | Insufficient memory | Remaining node resources insufficient |

### 4.2 Data Integrity Verification

Check data replica count and integrity after scale-in:

```bash
# Check data status in remaining node component logs
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<component_log_directory>' \
  -p 'log_file_name=<component_log_file>' \
  -p 'keywords=["replica","block","corrupt","missing","under-replicated","inconsistent","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common Issues**:

| Log Keyword | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Under-replicated | Insufficient replica count | Trigger replica supplement (e.g., HDFS setReplication) |
| Corrupt block | Data block corrupted | Repair or delete corrupted blocks |
| Missing block | Data block lost | Restore from backup |
| Inconsistent | Data inconsistent | Run data consistency check tool |

### 4.3 HA Configuration Update Verification

Check whether HA configuration has been updated to remove the scaled-in node:

```bash
# Check remaining node HA resource status
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ha-resource-status' \
  -p 'node_name=<oms_active_node>'
```

Also check HA logs for configuration update records:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=<ha_log_directory>' \
  -p 'log_file_name=<ha_log_file>' \
  -p 'keywords=["config","update","remove","member","node","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Criteria**:

| HA Status | Conclusion |
|-----------|------------|
| Running normally, scaled-in node removed from configuration | Scale-in successful |
| HA configuration still includes scaled-in node | Configuration not updated, need manual fix |
| HA resource abnormal | Need to check HA configuration and fix |

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Scaling in Active node without active/standby switchover | Controller logs have "Node is active" error; HA status is Active | Perform active/standby switchover first, confirm switchover success, then scale in |
| Insufficient data replicas causing data loss | Logs have "Replica not enough" or "Under-replicated"; data blocks lost after scale-in | Supplement replica count to safe threshold first, confirm data integrity, then scale in |
| Connections not drained causing service interruption | Port still listening with active connections; business reports connection failure | Drain connections first (graceful shutdown), wait for active connections to reach zero |
| HA configuration not updated | After scale-in, HA configuration still includes scaled-in node; HA status abnormal | Manually update HA configuration, remove scaled-in node information |
| Remaining node load too high | After scale-in, remaining nodes' CPU/memory/disk usage spikes | Evaluate capacity, scale out or adjust load balancing if necessary |
| Data migration failed | NodeAgent script logs have decommission/migrate ERROR | Check disk space and network, retry data migration |
| Other tasks running during scale-in | Controller logs have running/task/in progress | Wait for other tasks to complete before executing scale-in |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Scaled-in node name |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Scale-in operation time |
| <process_name> | Component config file | Process name in components/<service_name>.md |
| <port_number> | Component config file | Port in components/<service_name>.md |
| <ha_log_directory> | Component config file | HA role log directory in components/<service_name>.md |
| <ha_log_file> | Component config file | HA role log file name in components/<service_name>.md |
| <component_log_directory> | Component config file | Log directory in components/<service_name>.md |
| <component_log_file> | Component config file | Log file name in components/<service_name>.md |
