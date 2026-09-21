# Host Layer Diagnosis

> This file is loaded in step 2 of SKILL.md. The host layer is the bottom of the propagation chain -- if the host fails, all instances on it are affected.
> Use alarm diagnosis when there is an alarm; use status to fill in when there is no alarm.

## Diagnosis Flow

```
Step 1: Confirm host status (alarm + status)
  │
  ├─ Host isolated/suspended → Step 2
  ├─ Host unreachable (all API calls fail) → Step 3: Network/hardware fault troubleshooting
  ├─ Has 12006 alarm → Step 4: Reference 12006 alarm diagnosis
  ├─ No 12006 but resource abnormal (disk/memory/CPU) → Step 5: Resource troubleshooting
  └─ Host normal → Return to SKILL.md step 3 (instance layer troubleshooting)
```

## Step 1: Confirm Host Status (alarm + status)

> Basic data has already been collected in step 1 of SKILL.md and is used directly here.

### 1.1 Determine Host Status

Consolidate the data collected in step 1 of SKILL.md:

| Criterion | Result | Next Step |
|---------|------|--------|
| API calls in step 1.3-1.6 all fail or return exceptions | Node unreachable | Step 3 |
| Has 12006 alarm (detected in step 1.7) | Agent abnormal | Step 4 |
| Disk usage ≥100% | Disk full | Step 5 |
| Disk usage ≥85% | Disk almost full | Step 5 |
| Memory usage ≥95% | Insufficient memory | Step 5 |
| CPU load ≥ number of cores × 2 | CPU overloaded | Step 5 |
| Has 12007 alarm | Process fault (propagates to instance layer) | Return to SKILL.md step 3 |
| All of the above normal | Host normal | Return to SKILL.md step 3 |

> **When no alarm**: If step 1.7 does not detect a 12006 alarm, but API calls fail or resource metrics are abnormal, still follow status and go to step 3 or step 5.

### 1.2 Check Host Isolation Status

If the data returned by the API contains host isolation/suspension information:

| operationalState | Reason | Repair Suggestion |
|------------------|------|----------|
| ISOLATED | Host manually isolated or isolated due to disk | Confirm the isolation reason; release isolation via the Manager console |
| SUSPENDED | Host suspended | Confirm the suspension reason; recovery must be done via the Manager console |

---

## Step 2: Handling Isolated/Suspended Status

For an isolated/suspended host, its instances will be in UNKNOWN state. Record the propagation path:

```
Host isolated/suspended → all instances on it healthState=UNKNOWN, haState=UNKNOWN
```

Return to SKILL.md step 5 to output the propagation chain.

---

## Step 3: Network/Hardware Fault Troubleshooting (host unreachable)

> When all API calls in step 1 of SKILL.md fail, the host may be unreachable.

### 3.1 Query Node IP

```bash
python manager_api_client.py -a get_hosts -p 'hostname=<node_name>' --json
```

### 3.2 Ping the Fault Node from the OMS Active Node

```bash
# Manager mode has no standalone ping-check API; use check_remote to check remote node connectivity
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<target_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

### 3.3 Check Network Connectivity

```bash
# Manager mode has no standalone network-connectivity-test API; use check_remote to check network connectivity
python manager_api_client.py -a check_remote \
  -p 'remote_ip=<target_ip>' \
  -p 'remote_port=22' \
  -p 'remote_user_name=omm' \
  -p 'remote_client_path=/opt/huawei/Bigdata/nodeagent' --json
```

**Common root causes**:

| Root Cause | Characteristics | Repair Suggestion |
|------|------|----------|
| Host down | Cannot ping for a long time, no response | Contact the hardware administrator to check the server power and hardware status |
| Network link fault | A specific node cannot be pinged, other nodes fine | Contact the network administrator to check switches, cables, firewall |
| NIC fault | The node's own network interface is down | Log in to the host and check ifconfig/ip addr, restart the NIC |
| Gateway unreachable | Can ping the same subnet but not the gateway | Check the gateway and routing configuration |

---

## Step 4: Reference 12006 Alarm Diagnosis (NodeAgent process abnormal)

> **Reference alarm diagnosis document**: Load `../huawei-cloud-mrs-host-alarm-diagnose/alarm_manager/12006.md` and execute according to its diagnosis flow.
>
> **Parameter mapping**:
>
> | Variable in 12006 doc | Variable in this document |
> |------------------|---------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<alarm_time>` | `<alarm_time>` |
> | `<node_name>` | Fault node: `<node_name>`; OMS active node: `<oms_active_node>` |
> | `<alarm_node_ip>` | `<target_ip>` (obtained via get_hosts in step 3.1) |

---

## Step 5: Resource Troubleshooting (no 12006 alarm but resource abnormal)

> Execute when there is no 12006 alarm, but disk/memory/CPU metrics are abnormal.

According to the abnormal resource type detected in step 1, collect the corresponding data:

| Abnormal Item | Collection API | Threshold | Conclusion |
|--------|---------|------|------|
| Disk | get_host_detail | ≥100% | Disk full, clean up disk |
| Disk | get_host_detail | ≥85% | Disk almost full, clean up disk |
| Memory | get_host_detail | ≥95% | Insufficient memory, free or expand |
| CPU | get_host_metrics | ≥ cores × 2 | CPU overloaded, investigate high-CPU processes |
| Disk IO | get_host_detail | D-state process | Disk IO stuck, check storage device |
| Zombie process | get_host_process | Many Z-state | Investigate the parent process |

Data has already been collected in step 1.6 of SKILL.md and is used directly here.

**Resource abnormality propagation analysis**:

| Resource Abnormality | Impact on Instances | Propagation Path |
|---------|-----------|---------|
| Disk full | Process cannot write logs/data → process exit | Disk full → instance BAD → service may be BAD |
| Insufficient memory | OOM Kill → process disappears | Insufficient memory → OOM → instance BAD |
| CPU overloaded | Process responds slowly → health check timeout | CPU overloaded → health check timeout → instance BAD |
| Disk IO stuck | D-state process → cannot work normally | Disk IO → process D-state → instance UNKNOWN |

> Instance faults caused by resource abnormality have their root cause at the host layer. Return to SKILL.md step 5 to record the propagation path.

---

## Step 6: No Alarm but Host Status Abnormal

> When step 1.7 does not detect any alarm, but the host status is abnormal (e.g., abnormal API return data, some metrics near thresholds).

### 6.1 Check NodeAgent Logs

```bash
# Check ERROR and abnormal keywords in the NodeAgent agentlog log
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/nodeagent/agentlog/agent.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=ERROR' --json
```

### 6.2 Determine

| Log Keyword | Possible Cause | Repair Suggestion |
|------------|---------|---------|
| OutOfMemoryError | NodeAgent OOM | Expand memory or adjust NodeAgent JVM parameters |
| heartbeat timeout | Heartbeat timeout | Check network and OMS active node status |
| disconnected | Agent disconnected from Controller | Check network connectivity |
| No ERROR log | Host normal | Return to SKILL.md step 3 (instance layer troubleshooting) |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------|------|----------|----------|
| Host down/hardware fault | Cannot ping, no response | Contact the hardware administrator | — |
| Network fault | Cannot ping but the host may be online | Contact the network administrator to troubleshoot the link | — |
| Agent process abnormal | Has 12006 alarm | See the 12006 alarm diagnosis | `../huawei-cloud-mrs-host-alarm-diagnose/alarm_manager/12006.md` |
| Insufficient disk space | Disk usage ≥85% | Clean up disk or expand storage | — |
| Insufficient memory | dmesg has OOM records | Free memory or expand | — |
| Host isolated | operationalState=ISOLATED | Confirm the isolation reason, release via Manager | — |

## Variable Description

| Variable | Description | Example |
|------|------|------|
| `<cluster_id>` | MRS cluster ID | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<node_name>` | Fault host name | 8-5-225-6 |
| `<target_ip>` | Fault host IP | 8.5.225.6 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
