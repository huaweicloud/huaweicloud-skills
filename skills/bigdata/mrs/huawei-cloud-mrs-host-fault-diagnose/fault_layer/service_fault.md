# Service Layer Diagnosis

> This file is loaded at SKILL.md Step 4. The service layer is the top of the propagation chain — it checks the overall service status and dependency propagation. Use alarm cause code analysis when alarms exist; use instance status aggregation when no alarms; use alarm document fallback when all steps fail to locate the root cause.

## Diagnosis Flow

```
Step 1: Confirm service status (alarm + status)
  │
  ├─ Has service unavailable alarm → Step 2: Troubleshoot by alarm cause code
  │    ├─ Cause code 259-318 (dependency propagation) → Step 3: Dependency propagation tracing
  │    ├─ Cause code 286/222 (HDFS special) → Step 4: HDFS special troubleshooting
  │    ├─ Cause code 258/298/319/301-305 (instance-level) → Step 5: Locate faulty instance
  │    └─ Other business cause codes → Step 6: Business cause code troubleshooting
  │
  ├─ No alarm but service abnormal → Step 7: No-alarm status judgment
  │
  └─ Steps 1-7 all failed to locate root cause → Step 8: Fallback troubleshooting (load alarm docs for exhaustive check)
```

## Step 1: Confirm Service Status (Alarm + Status)

> Base data was collected in SKILL.md Step 1.

### 1.1 Check Alarms

> **Known limitation**: The `access_manager_get` interface returns a 500 error on some LakeWatch versions (e.g., 1.0.5).
> If the call fails, use the following alternative:

```bash
# Alternative: Detect service unavailable alarms via Controller logs
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","14000","16004","18000","18021","25000","25500","27001","service unavailable","healthState","BAD","raise alarm","depend service"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 1.2 Judgment

| Check Result | Conclusion | Next Step |
|--------------|------------|-----------|
| Logs have specific service unavailable alarm number (14000/16004/18000/18021/25000/25500/27001) | Has service unavailable alarm | Step 1.3: Reference alarm diagnosis document |
| Logs have service unavailable / raise alarm (no specific alarm number) | Has service unavailable alarm | Step 2 |
| Logs have healthState=BAD | Service status abnormal | Step 2 |
| Logs have depend service abnormal | Dependency propagation | Step 3 |
| No alarm keywords but multiple instances abnormal (detected in SKILL.md Step 1.3) | Service may be unavailable | Step 7 |
| No alarm and instances normal | Service normal | Return to SKILL.md Step 5 |

---

## Step 1.3: Reference Service Unavailable Alarm Diagnosis Document (When Specific Alarm Number Exists)

> **Reference alarm diagnosis document**: When a specific service unavailable alarm number is detected in logs, load the "alarm document reference" table in `components/<service_name>.md`,
> get the corresponding alarm document path, and follow the diagnosis flow in the alarm document.
>
> **Parameter Mapping**:
>
> | Variable in alarm doc | Variable in this doc |
> |-----------------------|---------------------|
> | `<cluster_id>` | `<cluster_id>` |
> | `<alarm_time>` | `<alarm_time>` |
> | `<node_name>` | `<node_name>` |
> | `<oms_active_node>` | `<oms_active_node>` |
> | `<service_name>` | `<service_name>` |

The alarm diagnosis document already contains the complete diagnosis flow for the service unavailability (log checks, cause code analysis, root cause location, etc.).
After executing the diagnosis in the alarm document, if you need to trace the propagation chain or assess impact scope, return to Steps 3-5 to continue.

---

## Step 2: Troubleshoot by Alarm Cause Code

### 2.1 Get Alarm Cause Code

Extract the alarm cause code from Controller logs:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","alarmCause","causeCode","reason","alarmId"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 2.2 Classify by Cause Code

| Cause Code Range | Type | Next Step |
|-----------------|------|-----------|
| 259-318 | Dependency propagation fault | Step 3 |
| 286, 222 | HDFS special fault | Step 4 |
| 258 | No Active instance | Step 5 |
| 298 | All instances abnormal | Step 5 |
| 319 | Majority instances abnormal | Step 5 |
| 301-305 | Process-level fault | Step 5 |
| 2 | Network fault | Step 6 |
| Other | Business error code | Step 6 |

---

## Step 3: Dependency Propagation Tracing

Cause code 259-318 indicates the service is unavailable due to dependency service fault propagation. Recursive tracing to the original fault source is needed.

**Dependency Propagation Cause Code Mapping**:

| Cause Code | Dependency Service |
|------------|-------------------|
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

**Tracing Flow**:

1. Determine the faulty dependency service based on cause code
2. Repeat Step 1 checks for that faulty service
3. If that service's cause code is still in the 259-318 range, continue recursive tracing
4. Trace until the cause code is 258/298/319/301-305 for the original fault
5. Original fault is instance-level → Step 5 (locate faulty instance, go to `instance_fault.md`)
6. Original fault is host-level → jump to `host_fault.md`

**Propagation Path Record**:
```
Hive(261 depends on HDFS unavailable) → HDFS(298 instances abnormal) → NameNode instance(305 PID does not exist) @ host-8-5-225-6
```

---

## Step 4: HDFS Special Troubleshooting (Cause Code 286/222)

### 4.1 Cause Code 286: All NameService Status Abnormal

Check process and port status for NameNode role instances (using data from SKILL.md Step 1.3-1.4):

| Phenomenon | Conclusion | Next Step |
|------------|------------|-----------|
| All NameNode processes do not exist | All NameNode failed | Go to Step 5 for each NameNode |
| Some NameNode processes exist but port not listening | Initialization failed | `instance_fault.md` Step 5 |
| Some NameNode normal but NameService still BAD | Configuration or dependency issue | Check ZKFC and JournalNode status |

### 4.2 Cause Code 222: Dependency on NameService Abnormal

Non-HDFS service depends on NameService status abnormal, a special case of dependency propagation.

**Repair Suggestion**: Fix HDFS NameService first, dependency services should recover automatically.

---

## Step 5: Locate Faulty Instance

Cause code 258/298/319/301-305 indicates instance-level fault causing service unavailable.

### 5.1 Locate Faulty Instance

Use the process status data collected in SKILL.md Step 1.3 to find instances with missing or abnormal processes.

For each non-normal instance:
1. Record process status, port status, HA status
2. If host unreachable → root cause is host fault, jump to `host_fault.md`
3. If host normal → go to `instance_fault.md` for instance diagnosis

### 5.2 Instance Aggregation Analysis

| Mode | Judgment Rule | Fault Threshold |
|------|--------------|-----------------|
| Active (active/standby) | Only look at Active instance | Active instance BAD means service BAD |
| Random | Randomly select one instance | Selected instance BAD means service BAD |
| All (any) | Any instance GOOD means service GOOD | All BAD means service BAD |
| Most (majority) | More than half GOOD means service GOOD | BAD instances >50% means service BAD |

### 5.3 Common Cause Analysis for Batch Instance Abnormalities

| Characteristic | Common Root Cause |
|---------------|-------------------|
| All abnormal instances on the same host | Host fault propagation |
| All abnormal instances on the same rack | Rack switch failure |
| Only specific role abnormal | Role-specific issue |
| All role instances abnormal | May be directory permission or disk issue |

---

## Step 6: Business Cause Code Troubleshooting

Non-standard cause codes are business-specific error codes:

| Cause Code | Meaning | Troubleshooting Direction |
|------------|---------|--------------------------|
| 2 | Network or hardware fault | Check network and hardware |
| 4/41 | Authentication failed | Check KrbServer |
| 5 | ZooKeeper read/write failed | Check ZooKeeper |
| 7 | DataNode service capacity insufficient | Check DataNode and disk |
| 8 | HDFS safe mode | Check HDFS safe mode |
| 9 | HDFS read/write failed | Check HDFS |
| 10 | HBase read/write failed | Check HBase |
| 15 | Database error | Check GaussDB |
| 34 | DBService HA abnormal | Check DBService HA |
| 36 | GaussDB access abnormal | Check GaussDB |
| 40 | ResourceManager abnormal | Check ResourceManager |
| 43 | LdapServer process abnormal | Check LdapServer |
| 46 | No available RegionServer | Check RegionServer |
| 47 | No active HMaster | Check HMaster |
| 99 | Lakesearch insufficient memory | Check Lakesearch process and memory |
| 100 | LakeSearch heartbeat abnormal | Check LakeSearch heartbeat |
| 320 | Core dump occurred | Check core dump file |

---

## Step 7: No-Alarm Status Judgment

> When there is no service unavailable alarm, but SKILL.md Step 1.3 detected multiple instance abnormalities.

### 7.1 Aggregate Instance Status

Use the process/port/HA data collected in SKILL.md Step 1.3-1.5, aggregate by service health check mode:

| Aggregation Result | Conclusion | Next Step |
|--------------------|------------|-----------|
| Active instance process does not exist | Service may be unavailable (Active mode) | Go to `instance_fault.md` for that instance |
| Majority instance processes do not exist | Service may be unavailable (Most mode) | Go to `instance_fault.md` for each abnormal instance |
| All instance processes do not exist | Service unavailable | Go to `instance_fault.md` for each instance |
| Some instances abnormal but service still available | Service sub-healthy | Record abnormal instances, go to `instance_fault.md` for diagnosis |

### 7.2 Check Dependency Services

```bash
# Check Controller logs for dependency service status
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","depend","dependency","required","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

### 7.3 Judgment

| Check Result | Conclusion | Next Step |
|--------------|------------|-----------|
| Dependency service process abnormal | Dependency propagation | Jump to Step 3 to trace dependency service |
| No dependency abnormality | Instance independent fault | Go to `instance_fault.md` for abnormal instances |
| All instances normal but service still abnormal | May be configuration or permission issue | Step 8: Fallback alarm document troubleshooting |

---

## Step 8: Fallback Troubleshooting (When All Steps Failed to Locate Root Cause)

> When Steps 1-7 all failed to locate the root cause, there may be faults that did not generate alarms (alarm delay, alarm loss, alarm rules not covering, etc.).
> At this point, load the corresponding service unavailable alarm diagnosis document based on `<service_name>`, and troubleshoot exhaustively following its complete diagnosis flow.

### 8.1 Load Alarm Diagnosis Document

Load `components/<service_name>.md`, check the "alarm document reference" table for the document path corresponding to the service unavailable alarm.

> If the component's configuration file does not exist or does not have alarm document references configured, inform the user that this component does not support fallback troubleshooting.

> The alarm document contains all known log check items, error keywords, root cause analysis, and repair methods for that service.
> Even without alarms generated, these check items are equally applicable to fault troubleshooting.

### 8.2 Execute Alarm Document Diagnosis

After loading the alarm document, follow its diagnosis flow to execute each step (log checks, process checks, configuration checks, dependency checks, etc.).

**Parameter Mapping**:

| Variable in alarm doc | Variable in this doc |
|-----------------------|---------------------|
| `<cluster_id>` | `<cluster_id>` |
| `<alarm_time>` | `<alarm_time>` |
| `<node_name>` | `<node_name>` |
| `<oms_active_node>` | `<oms_active_node>` |
| `<service_name>` | `<service_name>` |

### 8.3 Judgment

| Check Result | Conclusion | Next Step |
|--------------|------------|-----------|
| Alarm document diagnosis found root cause | Root cause located | Output diagnosis conclusion |
| Alarm document diagnosis still did not find root cause | Cannot automatically locate | Output items checked, suggest manual intervention |

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristics | Repair Suggestion | Detailed Reference |
|------------|-----------------|-------------------|---------------------|
| Dependency propagation fault | Cause code 259-318 | Trace to original fault source and fix, dependency services should recover automatically | — |
| Instance fault causing service unavailable | Cause code 258/298/319/301-305 | Locate faulty instance, go to instance fault diagnosis | `fault_layer/instance_fault.md` |
| HDFS NameService abnormal | Cause code 286/222 | Check NameNode/ZKFC/JournalNode status | — |
| Multiple instances on same host failed | Common cause analysis points to host | Jump to host fault diagnosis | `fault_layer/host_fault.md` |

## Variable Description

| Variable | Description | Example |
|----------|-------------|---------|
| `<cluster_id>` | MRS cluster identifier | 77b54fac-5e03-4713-9ac9-835d02d54e67 |
| `<service_name>` | Service name | HDFS |
| `<dep_service_name>` | Dependency service name (obtained from cause code mapping) | HDFS |
| `<node_name>` | Faulty host name | 8-5-225-6 |
| `<oms_active_node>` | OMS active node name | 8-5-225-6 |
| `<alarm_time>` | Fault time (format: yyyy/MM/dd HH:mm:ss GMT+X:XX) | 2026/07/13 10:00:00 GMT+08:00 |
