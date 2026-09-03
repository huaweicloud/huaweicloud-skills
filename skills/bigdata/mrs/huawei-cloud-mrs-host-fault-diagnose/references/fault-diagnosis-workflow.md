# Fault Diagnosis Workflow Design

This document describes the progressive fault diagnosis workflow design used by the MRS host fault diagnosis skill. It explains the three-layer fault model, the progressive investigation strategy, and the scenario identification mechanism.

## Overview

MRS cluster faults are categorized into three layers, each with a dedicated diagnosis document:

| Layer | Document | Description |
|-------|----------|-------------|
| Host | `fault_layer/host_fault.md` | Bottom layer — host reachability, resources (disk/memory/CPU), NodeAgent status |
| Instance | `fault_layer/instance_fault.md` | Middle layer — process, port, HA status; includes scenario identification |
| Service | `fault_layer/service_fault.md` | Top layer — service overall status, dependency propagation, alarm cause codes |

The propagation chain between layers is traced by `propagation.md`.

## Progressive Investigation Strategy

The skill follows a "quick first, deep later" approach:

```
Step 1: Locate fault object (entry routing)
  |
  +-- Step 2: Quick log scan (faulty instance/node)
  |     +-- Clear ERROR -> output root cause
  |     +-- Node unreachable / same-host pattern -> Step 3
  |     +-- No clear conclusion -> Step 4
  |
  +-- Step 3: Host troubleshooting -> fault_layer/host_fault.md
  |
  +-- Step 4: Detailed investigation
  |     +-- Data collection -> scenarios/data_collection.md
  |     +-- Instance layer diagnosis -> fault_layer/instance_fault.md
  |     +-- Service layer diagnosis -> fault_layer/service_fault.md
  |
  +-- Step 5: Propagation chain tracing -> propagation.md
  |
  +-- Step 6: Output diagnosis conclusion
```

**Why progressive?**

1. Quick log scan is fast — it checks Controller, NodeAgent, and component logs for clear ERROR keywords (OOM, permission denied, port conflict, etc.). If a clear ERROR is found, no further investigation is needed.
2. Host troubleshooting is needed when the quick scan shows the node is unreachable or multiple faulty instances concentrate on the same host.
3. Detailed investigation is the fallback — it collects complete data (process/port/HA/resource/alarm/framework logs) and performs systematic instance/service layer diagnosis.

## Entry Routing

The diagnosis entry is determined by the user-provided information:

| User Description | service_name | node_name | Entry | Step 1 Action |
|-----------------|-------------|-----------|-------|----------------|
| "KrbServer出问题了" | Yes | No | Service fault | Check all instances, find faulty ones |
| "8-5-225-6上的KrbServer挂了" | Yes | Yes | Instance fault | Directly check that instance |
| "8-5-225-6出问题了" | No | Yes | Host fault | Check host status, then instances on host |

## Scenario Identification (Instance Layer)

When the instance layer diagnosis identifies a process/port/HA abnormality without an alarm, it uses scenario identification to determine the operation context:

### Pure State Identification

| Process Status | Port Status | HA Status | Inferred Scenario | Confidence |
|---------------|-------------|-----------|-------------------|------------|
| Missing | Not listening | Stopped | stop (normal stop) | High |
| Missing | Not listening | Failed | stop failed or start failed | Medium |
| Missing | Still listening | — | stop incomplete | Medium |
| Present | Not listening | — | start failed (initializing) | Medium |
| Present | Listening | Non-Normal | HA abnormal | Medium |

### Framework Log Assisted Identification

When pure state cannot determine the scenario, framework logs (Controller exe.log + NodeAgent scriptlog) are used to identify the operation sequence:

| Log Operation Sequence | Actual Operation | Last Operation in Sequence |
|----------------------|-------------------|---------------------------|
| install -> start | Install (with auto-start) | start |
| uninstall -> stop | Uninstall (with stop) | uninstall |
| reinstall -> restore -> start | Reinstall | start |
| reinstall_host -> install -> start | Host reinstall | start |
| stop -> start | Restart | start |
| stop only | Stop | stop |
| scale_out -> install -> start | Scale out | start |
| scale_in -> stop -> decommission | Scale in | decommission |

### Supported Scenarios

| Scenario | Document | Key Checks |
|----------|----------|-------------|
| install | `scenarios/install.md` | Package integrity, config generation, directory permissions |
| start | `scenarios/start.md` | Pre-conditions (dependencies, config, port), health check |
| stop | `scenarios/stop.md` | Active connections, process exit, zombie/D-state |
| uninstall | `scenarios/uninstall.md` | Pre-stop, residual process/port/file, cleanup |
| reinstall | `scenarios/reinstall.md` | Backup, old component cleanup, config restore |
| reinstall_host | `scenarios/reinstall_host.md` | Base environment, NodeAgent, all component re-install |
| scale_out | `scenarios/scale_out.md` | New node environment, package distribution, data sync |
| scale_in | `scenarios/scale_in.md` | Active node check, data replica, connection drain |

All scenarios follow the 6-phase common framework defined in `scenarios/common.md`:
1. Operation confirmation
2. Controller execution chain check
3. Target node resource check
4. Component process and port check
5. Component log check
6. Scenario-specific checks

## Fault Propagation Model

MRS faults propagate across layers:

```
Host fault (bottom)
  |  Propagation: host BAD -> all instances on it become UNKNOWN
  v
Instance fault (middle)
  |  Propagation: instance BAD -> service health check may aggregate to BAD
  v
Service unavailable (top)
  |  Propagation: strong dependency BAD -> dependent service BAD
```

The propagation chain is traced by `propagation.md`, which:
1. Traces from current fault layer up/down to locate the original root cause
2. Evaluates the impact scope of the current fault on other layers
3. Outputs a complete propagation path in the diagnosis conclusion

## Component Configuration Model

Each component has a configuration file under `components/<service_name>.md` that provides:

| Section | Purpose |
|---------|---------|
| Component basic info | Service name, roles, process names, version, install user |
| Ports | Per-role port numbers |
| Log paths | Per-role log directories and file patterns |
| Install directories | Per-role installation paths |
| Data directories | Per-role data paths |
| Health check | Per-role check type and target |
| Dependencies | Strong/weak dependency service list |
| Scenario-specific checks | Per-scenario additional check items |
| Alarm document references | Mapping to alarm diagnosis documents |

The component config drives all scenario checks — different components automatically use different check parameters (process names, ports, log paths) within the same scenario.

> To support a new component, copy `components/_template.md`, rename it to `<service_name>.md`, and fill in the component information.
