# Service Layer Diagnosis

> This file is loaded in step 4 of SKILL.md. The service layer is the top of the propagation chain -- check the overall service status and dependency propagation.
> If there is an alarm, follow the alarm cause code troubleshooting; if no alarm, use the aggregated instance status for judgment; when no root cause is located in all steps, fall back to checking the alarm documents.

## Diagnosis Flow

```
Step 1: Confirm service status (alarm + status)
  │
  ├─ Has service-unavailable alarm → Step 2: Troubleshoot by alarm cause code
  │    ├─ Cause code 259-318 (dependency propagation) → Step 3: Dependency propagation tracing
  │    ├─ Cause code 286/222 (HDFS special) → Step 4: HDFS special troubleshooting
  │    ├─ Cause code 258/298/319/301-305 (instance-level) → Step 5: Locate the fault instance
  │    └─ Other business cause codes → Step 6: Business cause code troubleshooting
  │
  ├─ No alarm but service abnormal → Step 7: No-alarm status judgment
  │
  └─ Steps 1-7 all fail to locate a root cause → Step 8: Fallback troubleshooting (load alarm documents and check one by one)
```

## Step 1: Confirm Service Status (alarm + status)

> Basic data has already been collected in step 1 of SKILL.md.

### 1.1 Check Alarms

> **Known limitation**: The `get_alarms` API returns a 500 error in some Manager versions (e.g., 1.0.5).
> If the call fails, use the following alternative:

```bash
# Alternative: detect service-unavailable alarms through the Controller logs
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

### 1.2 Determine

| Check Result | Conclusion | Next Step |
|---------|------|--------|
| Log has a specific service-unavailable alarm number (14000/16004/18000/18021/25000/25500/27001) | Has service-unavailable alarm | Step 1.3: Reference the alarm diagnosis document |
| Log has service unavailable / raise alarm (no specific alarm number) | Has service-unavailable alarm | Step 2 |
| Log has healthState=BAD | Service status abnormal | Step 2 |
| Log has depend service abnormal | Dependency propagation | Step 3 |
| No alarm keywords but multiple instances abnormal (detected in step 1.3 of SKILL.md) | Service may be unavailable | Step 7 |
| No alarm and instances normal | Service normal | Return to SKILL.md step 5 |

---

## Step 1.3: Reference the Service-Unavailable Alarm Diagnosis Document (when there is a specific alarm number)

> **Reference alarm diagnosis document**: When a specific service-unavailable alarm number is detected in the logs, load the "alarm document reference" table in `components/<service_name>.md`,
> obtain the corresponding alarm document path, and execute according to the diagnosis flow in the alarm document.
>
> **Parameter mapping**:
>
> | Variable in alarm document | Variable in this document |
> |------------------|---------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<alarm_time>` | `<alarm_time>` |
> | `<node_name>` | `<node_name>` |
> | `<oms_active_node>` | `<oms_active_node>` |
> | `<service_name>` | `<service_name>` |

The alarm diagnosis document already contains the complete diagnosis flow for that service being unavailable (log checks, cause code analysis, root cause location, etc.).
After completing the diagnosis in the alarm document, return to steps 3-5 to continue if you need to trace the propagation chain or assess the scope of impact.

---

## Step 2: Troubleshoot by Alarm Cause Code

### 2.1 Obtain the Alarm Cause Code

Extract the alarm cause code from the Controller logs:

```bash
# Query the alarm cause code keyword in the Controller exe.log via browse_log
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=alarmCause' --json
```

### 2.2 Classify by Cause Code

| Cause Code Range | Type | Next Step |
|-----------|------|--------|
| 259-318 | Dependency propagation fault | Step 3 |
| 286, 222 | HDFS special fault | Step 4 |
| 258 | No Active instance | Step 5 |
| 298 | All instances abnormal | Step 5 |
| 319 | Most instances abnormal | Step 5 |
| 301-305 | Process-level fault | Step 5 |
| 2 | Network fault | Step 6 |
| Other | Business error code | Step 6 |

---

## Step 3: Dependency Propagation Tracing

Cause codes 259-318 indicate that the service is unavailable because a dependent service failed and propagated. It is necessary to recursively trace back to the original fault source.

**Dependency propagation cause code mapping**:

| Cause Code | Dependent Service |
|--------|----------|
| 259 | KrbServer |
| 260 | LdapServer |
| 261 | HDFS |
| 262 | ZooKeeper |
| 263 | Yarn |
| 264 | DBService |
| 265 | Mapreduce |
| 266 | Hue |
| 267 | Hive |
| 268-271 | Hive1-4 |
| 284 | HBase |
| 285-290 | HBase1-4 / Hive1-4 |
| 307 | Spark |
| 316 | MZooKeeper |
| 317 | FusionStorageHDFS |
| 318 | Kafka |
| 322 | ClickHouse |

**Tracing flow**:

1. Determine the dependent service that failed based on the cause code
2. Repeat the checks in step 1 for that failed service
3. If that service's cause code is still in the 259-318 range, continue recursive tracing
4. Continue until tracing back to the original fault with cause codes 258/298/319/301-305
5. If the original fault is instance-level → Step 5 (locate the fault instance, follow `instance_fault.md`)
6. If the original fault is host-level → jump to `host_fault.md`

**Propagation path record**:
```
Hive(261 depends on HDFS unavailable) → HDFS(298 instance abnormal) → NameNode instance(305 PID not present) @ host-8-5-225-6
```

---

## Step 4: HDFS Special Troubleshooting (cause codes 286/222)

### 4.1 Cause Code 286: All NameService Status Abnormal

Check the process and port status of the NameNode role instances (using data from steps 1.3-1.4 of SKILL.md):

| Phenomenon | Conclusion | Next Step |
|------|------|--------|
| All NameNode processes not present | All NameNodes failed | Go to step 5 for each NameNode |
| A NameNode process exists but the port is not listening | Initialization failed | `instance_fault.md` step 5 |
| A NameNode is normal but the NameService is still BAD | Config or dependency issue | Check the ZKFC and JournalNode status |

### 4.2 Cause Code 222: Abnormal Dependent NameService

The NameService status that a non-HDFS service depends on is abnormal; this is a special case of dependency propagation.

**Repair suggestion**: First repair the HDFS NameService; dependent services should recover automatically.

---

## Step 5: Locate the Fault Instance

Cause codes 258/298/319/301-305 indicate that an instance-level fault causes the service to be unavailable.

### 5.1 Locate the Fault Instance

Use the process status data collected in step 1.3 of SKILL.md to find instances whose process is not present or abnormal.

For each non-normal instance:
1. Record the process status, port status, and HA status
2. If the host is unreachable → the root cause is a host fault, jump to `host_fault.md`
3. If the host is normal → follow `instance_fault.md` to execute instance diagnosis

### 5.2 Instance Aggregation Analysis

| Mode | Judgment Rule | Fault Threshold |
|------|----------|----------|
| Active (active/standby) | Only look at the Active instance | The Active instance BAD means the service BAD |
| Random | Randomly select one instance | The selected instance BAD means the service BAD |
| All (any) | Any instance GOOD means the service GOOD | Only when all are BAD is the service BAD |
| Most (majority) | More than half GOOD means the service GOOD | BAD instances >50% means the service BAD |

### 5.3 Common-Cause Analysis of Batch Instance Abnormality

| Characteristic | Common Root Cause |
|------|----------|
| All abnormal instances on the same host | Host fault propagation |
| All abnormal instances on the same rack | Rack switch fault |
| Only a specific role abnormal | A specific issue of that role |
| All role instances abnormal | Possibly a directory permission or disk issue |

---

## Step 6: Business Cause Code Troubleshooting

Cause codes other than the standard ones are business-specific error codes:

| Cause Code | Meaning | Troubleshooting Direction |
|--------|------|----------|
| 2 | Network or hardware fault | Check the network and hardware |
| 4/41 | Authentication failure | Check KrbServer |
| 5 | ZooKeeper read/write failure | Check ZooKeeper |
| 7 | DataNode service capacity insufficient | Check DataNode and disk |
| 8 | HDFS safe mode | Check the HDFS safe mode |
| 9 | HDFS read/write failure | Check HDFS |
| 10 | HBase read/write failure | Check HBase |
| 15 | Database error | Check GaussDB |
| 34 | DBService HA abnormal | Check the DBService HA |
| 36 | GaussDB access abnormal | Check GaussDB |
| 40 | ResourceManager abnormal | Check ResourceManager |
| 43 | LdapServer process abnormal | Check LdapServer |
| 46 | No available RegionServer | Check RegionServer |
| 47 | No active HMaster | Check HMaster |
| 99 | Lakesearch insufficient memory | Check the Lakesearch process and memory |
| 100 | LakeSearch heartbeat abnormal | Check the LakeSearch heartbeat |
| 320 | Core dump occurred | Check the core dump file |

---

## Step 7: No-Alarm Status Judgment

> When there is no service-unavailable alarm, but step 1.3 of SKILL.md detects multiple instances abnormal.

### 7.1 Aggregate Instance Status

Use the process/port/HA data collected in steps 1.3-1.5 of SKILL.md, and aggregate according to the service health check mode:

| Aggregation Result | Conclusion | Next Step |
|---------|------|--------|
| The Active instance process is not present | Service may be unavailable (Active mode) | Follow `instance_fault.md` for that instance |
| Most instance processes not present | Service may be unavailable (Most mode) | Follow `instance_fault.md` for each abnormal instance |
| All instance processes not present | Service unavailable | Follow `instance_fault.md` for each instance |
| Some instances abnormal but the service still available | Service sub-healthy | Record the abnormal instances, follow `instance_fault.md` diagnosis |

### 7.2 Check Dependent Services

```bash
# Query the dependent service status in the Controller logs via browse_log
python manager_api_client.py -a browse_log \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=depend' --json
```

### 7.3 Determine

| Check Result | Conclusion | Next Step |
|---------|------|--------|
| Dependent service process abnormal | Dependency propagation | Jump to step 3 to trace the dependent service |
| No dependency abnormal | Instance fails independently | Follow `instance_fault.md` for the abnormal instance |
| All instances normal but the service still abnormal | Possibly a config or permission issue | Step 8: fallback troubleshooting through alarm documents |

---

## Step 8: Fallback Troubleshooting (when no step locates the root cause)

> When steps 1-7 all fail to locate a root cause, there may be a situation where there is a fault but no alarm was generated (alarm delay, alarm loss, alarm rule not covering, etc.).
> At this time, load the corresponding service-unavailable alarm diagnosis document according to `<service_name>`, and check item by item according to its complete diagnosis flow.

### 8.1 Load the Alarm Diagnosis Document

Load `components/<service_name>.md` and view the document path corresponding to the service-unavailable alarm in the "alarm document reference" table.

> If the component's config file does not exist or has no alarm document reference configured, inform the user that this component does not currently support fallback troubleshooting.

> The alarm document contains all known log check items, error keywords, root cause analysis, and repair methods for that service.
> Even if no alarm was generated, these check items are equally applicable to fault troubleshooting.

### 8.2 Execute the Alarm Document Diagnosis

After loading the alarm document, execute item by item according to its diagnosis flow (log check, process check, config check, dependency check, etc.).

**Parameter mapping**:

| Variable in alarm document | Variable in this document |
|------------------|---------------|
| `<cluster_id>` | `<cluster_id>` |
| `<alarm_time>` | `<alarm_time>` |
| `<node_name>` | `<node_name>` |
| `<oms_active_node>` | `<oms_active_node>` |
| `<service_name>` | `<service_name>` |

### 8.3 Determine

| Check Result | Conclusion | Next Step |
|---------|------|--------|
| The alarm document diagnosis found a root cause | Root cause located | Output the diagnosis conclusion |
| The alarm document diagnosis still did not find a root cause | Cannot auto-locate | Output the items already checked and suggest manual intervention |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------|------|----------|----------|
| Dependency propagation fault | Cause code 259-318 | Trace back to the original fault source and repair it; dependent services should recover automatically | — |
| Instance fault causing service unavailable | Cause code 258/298/319/301-305 | Locate the fault instance, follow the instance fault diagnosis | `instance_fault.md` |
| HDFS NameService abnormal | Cause code 286/222 | Check the NameNode/ZKFC/JournalNode status | — |
| Multiple instances on the same host fail | Common-cause analysis points to the host | Jump to the host fault diagnosis | `host_fault.md` |

## Variable Description

| Variable | Description | Example |
|------|------|------|
| `<cluster_id>` | MRS cluster ID | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<service_name>` | Service name | HDFS |
| `<dep_service_name>` | The name of the dependent service (obtained from the cause code mapping) | HDFS |
| `<node_name>` | Fault host name | 8-5-225-6 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
