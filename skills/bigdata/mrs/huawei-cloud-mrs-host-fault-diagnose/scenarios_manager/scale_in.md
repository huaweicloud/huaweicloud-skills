# Scale In Scenario Diagnosis

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Pre-Scale-In Safety Check
  │  ├─ 1.1 Role confirmation of the node to be scaled in (non-Active node)
  │  ├─ 1.2 Data replica integrity check
  │  └─ 1.3 Active task check (no tasks in progress)
  │
  ├─ Step 2: Service Migration Check
  │  ├─ 2.1 HA active/standby switchover check
  │  ├─ 2.2 Data redistribution check
  │  └─ 2.3 Connection draining check
  │
  ├─ Step 3: Scale-In Execution Check
  │  ├─ 3.1 Controller scale-in command log
  │  └─ 3.2 NodeAgent execution log
  │
  └─ Step 4: Post-Scale-In Verification
     ├─ 4.1 Remaining node health status
     ├─ 4.2 Data integrity verification
     └─ 4.3 HA configuration update verification
```

## Step 1: Pre-Scale-In Safety Check

**Goal**: Confirm that the node to be scaled in is in a safe and eligible state for scale-in, which will not cause data loss or service interruption

### 1.1 Role Confirmation of the Node to Be Scaled In

Check whether the node to be scaled in is an Active node (HA components must perform an active/standby switchover first):

```bash
# Check the HA resource status of the node to be scaled in
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<node_name>' --json
```

**Judgment criteria**:

| HA Resource Status | Eligible for Scale-In | Handling Suggestion |
|--------------------|-----------------------|---------------------|
| Standby | Yes | Scale in directly |
| Active | No | Perform an active/standby switchover first, then scale in |
| Single node (no HA) | Needs evaluation | Confirm whether the component supports single-node operation |

> **Note**: If the node to be scaled in is an Active node and an active/standby switchover was not performed, service interruption will result. This is the most common root cause in scale-in scenarios.

### 1.2 Data Replica Integrity Check

Check whether the data on the node to be scaled in has been synchronized to the remaining nodes, and confirm the replica count meets requirements:

```bash
# Check the process and data status of the node to be scaled in
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

Also check the NodeAgent script logs for data migration/synchronization related records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common Issues**:

| Log Keyword | Possible Cause | Risk Level |
|-------------|----------------|-----------|
| Replica not enough | Insufficient replica count, node cannot be removed | High - data loss risk |
| Sync not complete | Data synchronization not complete | High - data inconsistency |
| Rebalance failed | Data rebalancing failed | Medium - need manual retry |
| Under-replicated blocks | Insufficient replicas (HDFS scenario) | High - need to replenish replicas |

### 1.3 Active Task Check

Check whether there are tasks in progress in the cluster (e.g., balance, migration); wait for tasks to complete before scale-in:

```bash
# Check Controller logs for active task records
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Judgment criteria**:

| Controller Log | Conclusion | Handling Suggestion |
|----------------|------------|---------------------|
| No active task records | Safe | Can continue scale-in |
| Has running/in progress tasks | Unsafe | Wait for the task to complete or terminate manually |
| Has balance/migrate tasks | Unsafe | Wait for data balancing to complete |

---

## Step 2: Service Migration Check

**Goal**: Confirm that the services on the node to be scaled in have been correctly migrated to the remaining nodes

### 2.1 HA Active/Standby Switchover Check

Check whether the HA component has correctly completed the active/standby switchover (if the node to be scaled in was originally Active):

```bash
# Check the HA resource status of the remaining node
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<oms_active_node>' --json
```

Also check the HA logs for switchover records:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=failover' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

> **Tip**: The HA log directory and file names are obtained from the `log path` table in the component config file `components/<service_name>.md`.

**Common Issues**:

| HA Log Keyword | Possible Cause | Repair Suggestion |
|----------------|----------------|-------------------|
| Failover timeout | Active/standby switchover timed out | Check network and disk I/O, trigger switchover manually |
| Takeover failed | Takeover failed | Check the Standby node data consistency |
| Split-brain | Split-brain | Check heartbeat network, isolate the faulty node |
| No standby available | No available Standby node | Scale out first or promote another node to Standby |

### 2.2 Data Redistribution Check

Check whether data has been migrated from the node to be scaled in to the remaining nodes:

```bash
# Check the data migration logs on the node to be scaled in
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=decommission' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

**Judgment criteria**:

| Data Migration Status | Conclusion |
|-----------------------|------------|
| Decommission complete | Data migration complete, node can be safely removed |
| Decommission in progress | Data migration in progress, need to wait |
| Decommission failed | Data migration failed, need to investigate the cause |
| Under-replicated | Insufficient replicas, need to replenish replicas first |

### 2.3 Connection Draining Check

Check whether the active connections on the node to be scaled in have been drained:

```bash
# Check the network connection status of the node to be scaled in
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<target_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

Also check the port listening status to confirm whether the service has stopped accepting new requests:

```bash
# Check whether the component port is still listening
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json
```

**Judgment criteria**:

| Port Status | Active Connections | Conclusion |
|-------------|--------------------|------------|
| Still listening | Has active connections | Connections not drained, scale-in will interrupt services |
| Still listening | No active connections | Service can be stopped safely |
| Stopped listening | - | Service has stopped |

---

## Step 3: Scale-In Execution Check

**Goal**: Confirm that the scale-in command was correctly passed from Controller to NodeAgent and executed successfully

### 3.1 Controller Scale-In Command Log

Check the Controller logs for scale-in operation related records:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common ERROR keywords**:

| ERROR Keyword | Meaning | Possible Cause |
|---------------|---------|----------------|
| Node is active, cannot scale in | Node is Active, not allowed to scale in | Active/standby switchover not performed |
| Replica not enough | Insufficient replica count | Remaining replica count is below the minimum |
| Decommission failed | Data migration failed | Insufficient disk space or network abnormal |
| Agent timeout | NodeAgent response timeout | NodeAgent hung or under high load |
| Config update failed | Configuration update failed | HA configuration or cluster configuration update failed |
| Operation rejected | Operation rejected | Node status does not allow scale-in |

### 3.2 NodeAgent Execution Log

Check the process of NodeAgent executing the scale-in operation on the node to be scaled in:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Also check the NodeAgent script execution log:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Result mapping**:

| Controller Log | NodeAgent Log | Script Log | Conclusion |
|----------------|---------------|------------|------------|
| Has ERROR | — | — | Controller layer fault (e.g., pre-check failure) |
| Normal | Has ERROR | — | NodeAgent layer fault |
| Normal | Normal | Has ERROR | Script execution layer fault (e.g., cleanup failure) |
| Normal | Normal | Normal | Continue to Step 4 verification |

---

## Step 4: Post-Scale-In Verification

**Goal**: Confirm that after scale-in completes, the remaining nodes run normally, data is intact, and configurations have been updated

### 4.1 Remaining Node Health Status

Check the process, port, and resource status of the remaining nodes:

```bash
# Check the process status of the remaining node (execute for each remaining node)
python manager_api_client.py -a get_host_process \
  -p 'hostname=<oms_active_node>' --json

# Check the ports of the remaining node
# manager mode has no separate port check API
python manager_api_client.py -a get_host_process \
  -p 'hostname=<oms_active_node>' --json

# Check the resource load of the remaining node
python manager_api_client.py -a get_host_metrics \
  -p 'hostname=<oms_active_node>' \
  -p 'metric_names=dev_cpu_surp_avg,dev_load_one_min' --json

python manager_api_client.py -a get_host_detail \
  -p 'hostname=<oms_active_node>' --json
```

**Abnormal judgment**:

| Check Item | Threshold | Conclusion |
|------------|-----------|------------|
| Process does not exist | - | Scale-in caused abnormal service stop |
| Port not listening | - | Service did not start normally |
| CPU load ≥ cores×2 | Remaining node overloaded | Load too high after scale-in, need to scale out |
| Disk usage ≥ 85% | Disk about to be full | Data migration increased disk usage |
| Memory usage ≥ 95% | Insufficient memory | Insufficient resources on remaining nodes |

### 4.2 Data Integrity Verification

Check the data replica count and integrity after scale-in:

```bash
# Check the data status in the remaining node component logs
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=replica' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

**Common Issues**:

| Log Keyword | Possible Cause | Repair Suggestion |
|-------------|----------------|-------------------|
| Under-replicated | Insufficient replica count | Trigger replica replenishment (e.g., HDFS setReplication) |
| Corrupt block | Data block corrupted | Repair or delete the corrupted block |
| Missing block | Data block missing | Restore from backup |
| Inconsistent | Data inconsistent | Run the data consistency check tool |

### 4.3 HA Configuration Update Verification

Check whether the HA configuration has been updated to remove the node that was scaled in:

```bash
# Check the HA resource status of the remaining node
python manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' \
  -p 'service_name=<service_name>' \
  -p 'hostname=<oms_active_node>' --json
```

Also check the HA logs for configuration update records:

```bash
python manager_api_client.py -a start_log_search \
  -p 'cluster_id=<cluster_id>' \
  -p 'services=<component>:<service>:<role>' \
  -p 'min_log_level=WARN' \
  -p 'key_word=config' \
  -p 'start_time=<alarm_time>' \
  -p 'end_time=<current_time>' --json

python manager_api_client.py -a get_log_search_progress \
  -p 'search_id=<task_id>' --json
```

**Judgment criteria**:

| HA Status | Conclusion |
|-----------|------------|
| Running normally, the scaled-in node removed from configuration | Scale-in succeeded |
| HA configuration still contains the scaled-in node | Configuration not updated, need to fix manually |
| HA resource abnormal | Need to check HA configuration and fix it |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Active node scaled in without active/standby switchover | Controller logs have "Node is active" error; HA status is Active | Perform an active/standby switchover first, confirm success, then scale in |
| Data loss caused by insufficient data replicas | Logs have "Replica not enough" or "Under-replicated"; data blocks lost after scale-in | Replenish replica count to the safe threshold first, confirm data integrity, then scale in |
| Service interruption caused by undrained connections | Port still listening with active connections; business reports connection failures | Drain connections first (graceful shutdown), wait for active connections to reach zero |
| HA configuration not updated | HA configuration still contains the scaled-in node after scale-in; HA status abnormal | Manually update HA configuration, remove the scaled-in node information |
| Remaining node load too high | CPU/memory/disk usage of remaining nodes spikes after scale-in | Evaluate capacity, scale out or adjust load balancing if necessary |
| Data migration failed | NodeAgent script logs have decommission/migrate ERROR | Check disk space and network, retry data migration |
| Other tasks running during scale-in | Controller logs have running/task/in progress | Wait for other tasks to complete before performing scale-in |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Node to be scaled in |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Scale-in operation time |
| <process_name> | Component config file | Process name in components/<service_name>.md |
| <port> | Component config file | Port in components/<service_name>.md |
| <HA_log_directory> | Component config file | Log directory of the HA role in components/<service_name>.md |
| <HA_log_file> | Component config file | Log file name of the HA role in components/<service_name>.md |
| <component_log_directory> | Component config file | Log directory in components/<service_name>.md |
| <component_log_file> | Component config file | Log file name in components/<service_name>.md |
