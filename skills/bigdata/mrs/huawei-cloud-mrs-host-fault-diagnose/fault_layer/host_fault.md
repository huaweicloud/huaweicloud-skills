# Host Layer Diagnosis

> This file is loaded at SKILL.md Step 4. The host layer is the bottom of the propagation chain — if the host is faulty, all instances on it are affected. Use alarm-driven diagnosis when alarms exist; use status-driven when no alarms.

## Diagnosis Flow

```
Step 1: Confirm host status (alarm + status)
  │
  ├─ Host isolated/suspended → Step 2
  ├─ Host unreachable (all API calls fail) → Step 3: Network/hardware troubleshooting
  ├─ Has 12006 alarm → Step 4: Reference 12006 alarm diagnosis
  ├─ No 12006 but resource abnormal (disk/memory/CPU) → Step 5: Resource troubleshooting
  └─ Host normal → Return to SKILL.md Step 3 (instance layer troubleshooting)
```

## Step 1: Confirm Host Status (Alarm + Status)

> Base data was collected in SKILL.md Step 1, use it directly here.

### 1.1 Determine Host Status

Comprehensively use the data collected in SKILL.md Step 1:

| Criteria | Result | Next Step |
|----------|--------|-----------|
| All API calls from Step 1.3-1.6 fail or return errors | Node unreachable | Step 3 |
| Has 12006 alarm (detected in Step 1.7) | Agent abnormal | Step 4 |
| Disk usage ≥100% | Disk full | Step 5 |
| Disk usage ≥85% | Disk nearly full | Step 5 |
| Memory usage ≥95% | Insufficient memory | Step 5 |
| CPU load ≥ cores × 2 | CPU overload | Step 5 |
| Has 12007 alarm | Process fault (propagates to instance layer) | Return to SKILL.md Step 3 |
| All above normal | Host normal | Return to SKILL.md Step 3 |

> **When no alarm**: If Step 1.7 did not detect a 12006 alarm, but API calls fail or resource metrics are abnormal, still proceed to Step 3 or Step 5 based on status.

### 1.2 Check Host Isolation Status

If the API return data contains host isolation/suspension information:

| operationalState | Cause | Repair Suggestion |
|------------------|-------|-------------------|
| ISOLATED | Host manually isolated or disk isolated | Confirm isolation reason, removing isolation requires Manager interface operation |
| SUSPENDED | Host suspended | Confirm suspension reason, recovery requires Manager interface operation |

---

## Step 2: Isolation/Suspension Status Handling

For isolated/suspended hosts, their instances will be in UNKNOWN status. Record the propagation path:

```
Host isolated/suspended → All instances on it healthState=UNKNOWN, haState=UNKNOWN
```

Return to SKILL.md Step 5 to output the propagation chain.

---

## Step 3: Network/Hardware Troubleshooting (Host Unreachable)

> When all API calls in SKILL.md Step 1 fail, the host may be unreachable.

### 3.1 Query Node IP

```bash
python lakewatch_api_client.py -a query-node-ip \
  -p 'cluster_id=<cluster_id>' \
  -p 'node_name=<node_name>'
```

### 3.2 Ping Faulty Node from OMS Active Node

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=ping-check' \
  -p 'env={"TARGET_IP":"<target_ip>"}' \
  -p 'node_name=<oms_active_node>'
```

### 3.3 Check Network Connectivity

```bash
python lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=network-connectivity-test' \
  -p 'env={"TARGET_IP":"<target_ip>"}' \
  -p 'node_name=<oms_active_node>'
```

**Common Root Causes**:

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Host down | Long-time ping failure, no response | Contact hardware administrator to check server power and hardware status |
| Network link failure | Specific node ping fails, other nodes normal | Contact network administrator to check switches, cables, firewalls |
| NIC failure | Node's own network interface down | Log in to host to check ifconfig/ip addr, restart NIC |
| Gateway unreachable | Can ping same subnet but cannot ping gateway | Check gateway and routing configuration |

---

## Step 4: Reference 12006 Alarm Diagnosis (NodeAgent Process Abnormal)

> **Reference alarm diagnosis document**: Load `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12006.md`, follow its diagnosis flow.
>
> **Parameter Mapping**:
>
> | Variable in 12006 doc | Variable in this doc |
> |-----------------------|---------------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<alarm_time>` | `<alarm_time>` |
> | `<node_name>` | Faulty node: `<node_name>`; OMS active node: `<oms_active_node>` |
> | `<alarm_node_ip>` | `<target_ip>` (obtained via query-node-ip in Step 3.1) |

---

## Step 5: Resource Troubleshooting (No 12006 Alarm but Resource Abnormal)

> Execute when there is no 12006 alarm, but disk/memory/CPU metrics are abnormal.

Based on the abnormal resource type detected in Step 1, collect corresponding data:

| Abnormal Item | Collection strategy | Threshold | Conclusion |
|---------------|---------------------|-----------|------------|
| Disk | disk-space | ≥100% | Disk full, clean up disk |
| Disk | disk-space | ≥85% | Disk nearly full, clean up disk |
| Memory | memory-usage | ≥95% | Insufficient memory, release or expand |
| CPU | system-load | ≥ cores × 2 | CPU overload, troubleshoot high CPU processes |
| Disk IO | disk-io | D-state processes | Disk IO stuck, check storage devices |
| Zombie processes | zombie-process | Large number of Z-state | Troubleshoot parent process |

Data was collected in SKILL.md Step 1.6, use it directly here.

**Resource Abnormal Propagation Analysis**:

| Resource Abnormal | Impact on Instances | Propagation Path |
|-------------------|---------------------|-----------------|
| Disk full | Process cannot write logs/data → process exits | Disk full → instance BAD → service may be BAD |
| Insufficient memory | OOM Kill → process disappears | Insufficient memory → OOM → instance BAD |
| CPU overload | Process responds slowly → health check timeout | CPU overload → health check timeout → instance BAD |
| Disk IO stuck | D-state process → cannot work normally | Disk IO → process D-state → instance UNKNOWN |

> For instance faults caused by resource abnormalities, the root cause is at the host layer. Return to SKILL.md Step 5 to record the propagation path.

---

## Step 6: No Alarm but Host Status Abnormal

> When Step 1.7 did not detect any alarm, but host status is abnormal (e.g., API returns abnormal data, some metrics near threshold).

### 6.1 Check NodeAgent Logs

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'alarm_duration_minutes=60' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/agentlog/' \
  -p 'log_file_name=agent*' \
  -p 'keywords=["ERROR","Exception","OutOfMemoryError","Out of memory","heartbeat","disconnected","timeout"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

### 6.2 Judgment

| Log Keywords | Possible Cause | Repair Suggestion |
|--------------|----------------|-------------------|
| OutOfMemoryError | NodeAgent OOM | Expand memory or adjust NodeAgent JVM parameters |
| heartbeat timeout | Heartbeat timeout | Check network and OMS active node status |
| disconnected | Agent disconnected from Controller | Check network connectivity |
| No ERROR logs | Host normal | Return to SKILL.md Step 3 (instance layer troubleshooting) |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------------|-----------------|-------------------|---------------------|
| Host down/hardware failure | Ping fails, no response | Contact hardware administrator | — |
| Network failure | Ping fails but host may be online | Contact network administrator to troubleshoot link | — |
| Agent process abnormal | Has 12006 alarm | See 12006 alarm diagnosis | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12006.md` |
| Insufficient disk space | Disk usage ≥85% | Clean up disk or expand | — |
| Insufficient memory | dmesg has OOM records | Release memory or expand | — |
| Host isolated | operationalState=ISOLATED | Confirm isolation reason, removing isolation requires Manager interface operation | — |

## Variable Description

| Variable | Description | Example |
|----------|-------------|---------|
| `<cluster_id>` | MRS cluster identifier | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<node_name>` | Faulty host name | 8-5-225-6 |
| `<target_ip>` | Faulty host IP | 8.5.225.6 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
