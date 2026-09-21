# Propagation Chain Tracing Logic

> This file is loaded in step 5 of SKILL.md. After the three-layer diagnosis (host_fault → instance_fault → service_fault) is completed,
> use this file to trace the root-cause propagation path and the scope of impact.
>
> Core principle: comprehensively judge using alarm + status. Alarms may be missing (the fault causes the alarm to be not generated or delayed), so use status to fill in.

## Overview

In an MRS cluster, faults among the host, instance, and service layers have a propagation relationship. This file defines the tracing rules for the propagation chain, used to:
1. Trace upward/downward from the current fault layer to locate the original root cause
2. Assess the impact of the current fault on other layers
3. Output the complete propagation path in the diagnosis conclusion

## Propagation Relationship Model

```
Host fault (bottom layer)
  │  Propagation: Host BAD → all instances on it healthState=UNKNOWN
  │  Propagation: Host BAD → all instances on it haState=UNKNOWN
  ▼
Instance fault (middle layer)
  │  Propagation: Instance BAD → service may become BAD after health check aggregation
  │  Propagation: All instances of a critical role BAD → service BAD
  ▼
Service unavailable (top layer)
  │  Propagation: Strong-dependent service BAD → dependent service BAD
  │  Propagation: Strong-dependent service PARTIALLY_HEALTHY → dependent PARTIALLY_HEALTHY
  │  Propagation: Weak-dependent service abnormal → dependent PARTIALLY_HEALTHY
```

## Tracing Direction

### Trace Upward from Host Fault (assess impact)

When the diagnosis entry point is a host fault, it is necessary to assess the impact of that host fault on instances and services.

**Steps**:

1. Query all instances on that host

```bash
python manager_api_client.py -a get_host_process -p 'hostname=<node_name>' --json
```

2. Group by service to determine which services are affected

```bash
python manager_api_client.py -a get_cluster_services -p 'cluster_id=<cluster_id>' --json
```

3. For each affected service, determine based on the health check mode whether it will cause the service to be BAD

| Health Check Mode | Judgment Rule | Does a Host Fault Cause the Service to Be BAD |
|-------------|----------|----------------------|
| Active (active/standby) | Only look at the Active instance | Service BAD if the Active instance is on this host |
| Random | Randomly select one instance | Possibly BAD (depends on which one is randomly selected) |
| All (any) | Any instance GOOD means the service GOOD | BAD only when this host is the host of the only instance |
| Most (majority) | More than half GOOD means the service GOOD | Depends on whether BAD instances exceed half |

4. For each affected service, check whether it has strong-dependent parties

```bash
# Query active alarms for dependency propagation alarms
python manager_api_client.py -a get_alarms --json
```

**Example output propagation path**:
```
Host host-8-5-225-6 heartbeat timeout(BAD)
  → NameNode instance UNKNOWN
  → DataNode instance UNKNOWN
  → HDFS service BAD (Active mode, Active NameNode on this host)
    → Hive service BAD (strong-depend on HDFS, cause code 261)
    → Spark service BAD (strong-depend on HDFS, cause code 307)
```

---

### Bidirectional Tracing from Instance Fault

When the diagnosis entry point is an instance fault, it is necessary to:
- **Downward**: check whether the host where the instance resides has failed (the root cause may be on the host)
- **Upward**: check whether the instance fault causes the service to be unavailable (impact assessment)

**Trace downward (find the root cause)**:

1. Check the status of the host where the instance resides

```bash
python manager_api_client.py -a get_host_detail -p 'hostname=<node_name>' --json
```

| Host Status | Conclusion | Propagation Path |
|----------|------|----------|
| BAD | The root cause is a host fault | Host fault → instance UNKNOWN |
| GOOD | The instance fails independently | No propagation, the instance is the root cause |

2. If the host is BAD, jump to `fault_layer_manager/host_fault.md` to continue diagnosing the host fault

**Trace upward (assess impact)**:

1. Determine the service to which the instance belongs
2. Query the status of other instances of that service

```bash
python manager_api_client.py -a get_instances -p 'cluster_id=<cluster_id>' -p 'service_name=<service_name>' --json
```

3. Determine based on the health check mode whether the service is affected

4. If the service is BAD, check whether there is dependency propagation

**Example output propagation path**:
```
NameNode instance @ host-8-5-225-6 process crash(BAD, cause code 305)
  → HDFS service BAD (Active mode, Active NameNode fault)
    → Hive service BAD (strong-depend on HDFS)
```

Or:

```
Host host-8-5-225-6 heartbeat timeout(BAD)
  → NameNode instance UNKNOWN (propagated, not an independent fault)
  → HDFS service BAD
```

---

### Trace Downward from Service Unavailable (locate the root cause)

When the diagnosis entry point is service unavailable, it is necessary to trace downward to locate the original fault source.

**Steps**:

1. Obtain the service alarm cause code

2. Determine based on the cause code whether it is a propagation fault

| Cause Code Range | Nature | Tracing Direction |
|-----------|------|----------|
| 259-318 | Dependency propagation | Recursively trace the dependent service |
| 286, 222 | HDFS special | Trace back to the NameNode instance |
| 258 | No Active instance | Trace back to the HA role instance |
| 298 | All instances abnormal | Trace back to the specific fault instance |
| 319 | Most instances abnormal | Trace back to the specific fault instance |
| 301-305 | Process-level fault | Trace back to the checker of the specific instance |
| 2 | Network fault | Trace back to the host network |
| Other | Business error code | Trace according to the meaning of the business code |

3. Recursive tracing of dependency propagation

```
Current service A cause code = 261 (depends on HDFS)
  → Query HDFS status → HDFS BAD, cause code = 298 (instance abnormal)
    → Query all HDFS instances → NameNode @ host-X BAD, cause code = 305 (PID not present)
      → Original root cause: NameNode process crash, located on host-X
      → Propagation chain: NameNode process crash → HDFS unavailable → Hive unavailable
```

4. Downward tracing of instance-level faults

For each non-GOOD instance:
- Check the host status → if the host is BAD, the root cause is a host fault
- If the host is GOOD, the root cause is an independent instance fault → follow `instance_fault.md`

5. Check whether there are multiple root causes

If multiple instances distributed across different hosts are all BAD:
- Check whether there is a common characteristic (same rack, same disk, same network)
- It may be multiple independent faults or an infrastructure issue

**Example output propagation path**:
```
Hive service BAD (cause code 261: depends on HDFS unavailable)
  → HDFS service BAD (cause code 298: instance abnormal)
    → NameNode instance @ host-8-5-225-6 BAD (cause code 305: PID not present)
      → Root cause: NameNode process OOM Kill
```

---

## Propagation Impact Assessment Rules

### Strong-Dependency Propagation

| Dependent Service Status | Dependent-Party Result |
|--------------|-----------|
| BAD or stopped | Dependent party BAD |
| PARTIALLY_HEALTHY | Dependent party PARTIALLY_HEALTHY |
| Does not exist (non-optional dependency) | Dependent party BAD |

### Weak-Dependency Propagation

| Dependent Service Status | Dependent-Party Result |
|--------------|-----------|
| Abnormal (non-HEALTH+ACTIVE) | Dependent party PARTIALLY_HEALTHY (does not escalate to BAD) |

### Host Fault Propagation

| Host Status | Instance Result | Service Result |
|----------|----------|----------|
| BAD | All instances on this host healthState=UNKNOWN, haState=UNKNOWN | Determined according to the health check mode |

### Instance Fault Propagation

| Instance Status | Service Result (depends on the check mode) |
|----------|--------------------------|
| Single BAD (Active mode and it is the Active instance) | Service BAD |
| Single BAD (All mode) | Service may still be GOOD (other instances GOOD) |
| Most BAD (Most mode) | Service BAD |
| All BAD | Service BAD |

---

## Propagation Chain Output Format

In the diagnosis conclusion, the propagation path uses the following format:

### Single-Root-Cause Propagation

```
[Root cause] → [Propagation 1] → [Propagation 2] → [Manifestation]

Example:
NameNode process OOM Kill @ host-8-5-225-6 → NameNode instance BAD → HDFS service BAD → Hive service BAD
```

### Multiple Root Causes

```
[Root cause 1] ─┐
          ├→ [Common manifestation]
[Root cause 2] ─┘

Example:
DataNode instance BAD @ host-8-5-225-6 ─┐
                                    ├→ HDFS service BAD (Most mode, BAD instances >50%)
DataNode instance BAD @ host-8-5-225-7 ─┘
```

### Propagation + Independent Fault

```
[Propagated root cause] → [Propagated manifestation]
[Independent fault] (no propagation relationship)

Example:
Host host-8-5-225-6 heartbeat timeout → NameNode instance UNKNOWN → HDFS service BAD
Hive MetaStore instance BAD @ host-8-5-225-7 (independent fault, not propagated)
```
