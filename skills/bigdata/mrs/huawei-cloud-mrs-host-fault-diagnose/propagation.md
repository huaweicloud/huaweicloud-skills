# Propagation Chain Tracing Logic

> This file is loaded at SKILL.md Step 5. After the three-layer diagnosis (host_fault -> instance_fault -> service_fault) is complete, this file traces the root cause propagation path and impact scope.
>
> Core principle: comprehensive judgment with alarms + status. Alarms may be missing (faults may prevent alarm generation or cause delays), use status to supplement.

## Overview

In MRS clusters, host, instance, and service layer faults have propagation relationships. This file defines the tracing rules for propagation chains, used to:
1. Trace from the current fault layer up/down to locate the original root cause
2. Assess the impact scope of the current fault on other layers
3. Output the complete propagation path in the diagnosis conclusion

## Propagation Relationship Model

```
Host fault (bottom layer)
  │  Propagation: host BAD → all instances on it healthState=UNKNOWN
  │  Propagation: host BAD → all instances on it haState=UNKNOWN
  ▼
Instance fault (middle layer)
  │  Propagation: instance BAD → service health check aggregated may be BAD
  │  Propagation: all instances BAD for critical role → service BAD
  ▼
Service unavailable (top layer)
  │  Propagation: strong dependency service BAD → dependent service BAD
  │  Propagation: strong dependency service PARTIALLY_HEALTHY → dependent PARTIALLY_HEALTHY
  │  Propagation: weak dependency service abnormal → dependent PARTIALLY_HEALTHY
```

## Tracing Direction

### Tracing Upward from Host Fault (Impact Assessment)

When the diagnosis entry point is host fault, the impact of the host fault on instances and services needs to be assessed.

**Steps**:

1. Query all instances on that host

```bash
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/hosts/<node_name>/processes'
```

2. Group by service, determine which services are affected

```bash
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services'
```

3. For each affected service, determine whether it will cause service BAD based on health check mode

| Health Check Mode | Judgment Rule | Whether Host Fault Causes Service BAD |
|-------------------|--------------|--------------------------------------|
| Active (active/standby) | Only look at Active instance | If Active instance is on that host, service BAD |
| Random | Randomly select one instance | May be BAD (depends on which is randomly selected) |
| All (any) | Any instance GOOD means service GOOD | Only BAD when that host is the only instance host |
| Most (majority) | More than half GOOD means service GOOD | Depends on whether BAD instances exceed half |

4. For each affected service, check whether it has strong dependents

```bash
# Query active alarms for dependency propagation alarms
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/alarms'
```

**Propagation Path Output Example**:
```
Host host-8-5-225-6 heartbeat timeout (BAD)
  → NameNode instance UNKNOWN
  → DataNode instance UNKNOWN
  → HDFS service BAD (Active mode, Active NameNode on that host)
    → Hive service BAD (strong dependency on HDFS, cause code 261)
    → Spark service BAD (strong dependency on HDFS, cause code 307)
```

---

### Bidirectional Tracing from Instance Fault

When the diagnosis entry point is instance fault, need to:
- **Downward**: Check whether the host where the instance resides is faulty (root cause may be at host)
- **Upward**: Check whether the instance fault causes service unavailability (impact assessment)

**Downward Tracing (Find Root Cause)**:

1. Check host status where instance resides

```bash
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/hosts?hostName=<node_name>'
```

| Host Status | Conclusion | Propagation Path |
|-------------|------------|------------------|
| BAD | Root cause is host fault | Host fault → instance UNKNOWN |
| GOOD | Instance independent fault | No propagation, instance is root cause |

2. If host BAD, jump to `fault_layer/host_fault.md` to continue host fault diagnosis

**Upward Tracing (Assess Impact)**:

1. Determine the service the instance belongs to
2. Query other instances' status for that service

```bash
python lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services/<service_name>/instances'
```

3. Determine whether the service is affected based on health check mode
4. If service BAD, check whether there is dependency propagation

**Propagation Path Output Example**:
```
NameNode instance @ host-8-5-225-6 process crash (BAD, cause code 305)
  → HDFS service BAD (Active mode, Active NameNode fault)
    → Hive service BAD (strong dependency on HDFS)
```

Or:

```
Host host-8-5-225-6 heartbeat timeout (BAD)
  → NameNode instance UNKNOWN (propagation, not independent fault)
  → HDFS service BAD
```

---

### Tracing Downward from Service Unavailability (Locate Root Cause)

When the diagnosis entry point is service unavailability, need to trace downward to locate the original fault source.

**Steps**:

1. Get service alarm cause code

2. Determine whether it is a propagation fault based on cause code

| Cause Code Range | Nature | Tracing Direction |
|-----------------|--------|-------------------|
| 259-318 | Dependency propagation | Recursively trace dependency service |
| 286, 222 | HDFS special | Trace to NameNode instance |
| 258 | No Active instance | Trace to HA role instance |
| 298 | All instances abnormal | Trace to specific faulty instance |
| 319 | Majority instances abnormal | Trace to specific faulty instance |
| 301-305 | Process-level fault | Trace to specific instance's checker |
| 2 | Network fault | Trace to host network |
| Other | Business error code | Trace based on business code meaning |

3. Recursive tracing of dependency propagation

```
Current service A cause code=261 (depends on HDFS)
  → Query HDFS status → HDFS BAD, cause code=298 (instances abnormal)
    → Query all HDFS instances → NameNode @ host-X BAD, cause code=305 (PID does not exist)
      → Original root cause: NameNode process crash, located on host-X
      → Propagation chain: NameNode process crash → HDFS unavailable → Hive unavailable
```

4. Downward tracing of instance-level faults

For each non-GOOD instance:
- Check host status → host BAD means root cause is host fault
- Host GOOD means root cause is instance independent fault → go to `instance_fault.md`

5. Check for multiple root causes

If multiple instances on different hosts are all BAD:
- Check for commonality (same rack, same disk, same network)
- May be multiple independent faults, or may be infrastructure issue

**Propagation Path Output Example**:
```
Hive service BAD (cause code 261: depends on HDFS unavailable)
  → HDFS service BAD (cause code 298: instances abnormal)
    → NameNode instance @ host-8-5-225-6 BAD (cause code 305: PID does not exist)
      → Root cause: NameNode process OOM Killed
```

---

## Propagation Impact Assessment Rules

### Strong Dependency Propagation

| Dependency Service Status | Dependent Result |
|--------------------------|------------------|
| BAD or stopped | Dependent BAD |
| PARTIALLY_HEALTHY | Dependent PARTIALLY_HEALTHY |
| Does not exist (non-optional dependency) | Dependent BAD |

### Weak Dependency Propagation

| Dependency Service Status | Dependent Result |
|--------------------------|------------------|
| Abnormal (non-HEALTH+ACTIVE) | Dependent PARTIALLY_HEALTHY (not elevated to BAD) |

### Host Fault Propagation

| Host Status | Instance Result | Service Result |
|-------------|-----------------|----------------|
| BAD | All instances on that host healthState=UNKNOWN, haState=UNKNOWN | Judge based on health check mode |

### Instance Fault Propagation

| Instance Status | Service Result (depends on check mode) |
|-----------------|---------------------------------------|
| Single BAD (Active mode and is Active instance) | Service BAD |
| Single BAD (All mode) | Service may still be GOOD (other instances GOOD) |
| Majority BAD (Most mode) | Service BAD |
| All BAD | Service BAD |

---

## Propagation Chain Output Format

In the diagnosis conclusion, propagation paths use the following format:

### Single Root Cause Propagation

```
[Root Cause] → [Propagation 1] → [Propagation 2] → [Symptom]

Example:
NameNode process OOM Killed @ host-8-5-225-6 → NameNode instance BAD → HDFS service BAD → Hive service BAD
```

### Multiple Root Causes

```
[Root Cause 1] ─┐
                 ├→ [Common Symptom]
[Root Cause 2] ─┘

Example:
DataNode instance BAD @ host-8-5-225-6 ─┐
                                         ├→ HDFS service BAD (Most mode, BAD instances >50%)
DataNode instance BAD @ host-8-5-225-7 ─┘
```

### Propagation + Independent Fault

```
[Propagation Root Cause] → [Propagation Symptom]
[Independent Fault] (no propagation relationship)

Example:
Host host-8-5-225-6 heartbeat timeout → NameNode instance UNKNOWN → HDFS service BAD
Hive MetaStore instance BAD @ host-8-5-225-7 (independent fault, not propagation)
```
