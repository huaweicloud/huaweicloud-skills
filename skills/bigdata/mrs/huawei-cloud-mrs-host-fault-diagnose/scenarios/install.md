# Install Scenario Specific Checks

> Prerequisites: Completed common checks from Phases 1-5 in common.md
> Component config: Load `components/<service_name>.md` for component information

## Diagnosis Flow

```
Step 1: Installation Package Integrity Check
  │
  ├─ Step 2: Configuration File Generation Check
  │
  ├─ Step 3: Directory Permission and Data Initialization Check
  │
  └─ Step 4: Post-Install Verification
```

## Step 1: Installation Package Integrity Check

Check the Controller logs for errors related to installation package distribution and extraction:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["<service_name>","install","package","distribute","extract","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<oms_active_node>'
```

**Common Issues**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|----------------|-------------------|
| Package not found | Installation package not distributed to node | Check packages directory, redistribute |
| Extract failed | Insufficient disk space or corrupted package | Clean up disk, verify SHA256 |
| Permission denied | Distribution directory permission abnormal | Check /opt/huawei/Bigdata/packages permissions |
| Checksum mismatch | Installation package corrupted | Re-download installation package |

---

## Step 2: Configuration File Generation Check

Check the NodeAgent script logs for configuration generation related errors:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","config","genConfig","ERROR","fail"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

Also check whether configuration files have been generated in the component instance directory:
- Check path: `$BIGDATA_HOME/FusionInsight_Current/<instance_number>_<role>/etc/`
- Check file: whether configurations.xml exists

---

## Step 3: Directory Permission and Data Initialization Check

### 3.1 Installation Directory Permission Check

Check the NodeAgent script logs for directory permission related errors and confirm installation directory permissions are correct:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","permission","chmod","chown","owner","denied","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

> **Note**: LakeWatch API does not have a strategy to directly check file permissions. This is indirectly determined through permission-related keywords in script logs.

### 3.2 Data Directory Initialization

For components with data directories (e.g., DBService's `/srv/BigData/dbdata_service/data`),
check whether the data directory has been correctly initialized.

Check the NodeAgent script logs for initialization related content:

```bash
python lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=<alarm_time>' \
  -p 'log_directory=/var/log/Bigdata/nodeagent/scriptlog' \
  -p 'log_file_name=*.log*' \
  -p 'keywords=["<service_name>","init","initialize","ERROR"]' \
  -p 'log_type=local' \
  -p 'node_name=<node_name>'
```

---

## Step 4: Post-Install Verification

### 4.1 Process and Port Verification

After installation, the component usually auto-starts. Check processes and ports per common.md Phase 4.

### 4.2 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Install` section of the component config file,
load the component config and execute each check item.

For each check item, select the appropriate API call based on the described check content:
- Process/port check → `collect_alarm_node_res_data` (process-basic-info / port-check)
- Log check → `collect_alarm_log_data`
- HA status → `collect_alarm_node_res_data` (ha-resource-status)

---

## Typical Root Causes

| Root Cause | Characteristics | Repair Suggestion |
|------------|-----------------|-------------------|
| Installation package missing or corrupted | Controller logs have Package not found | Redistribute installation package, verify SHA256 |
| Insufficient disk space | disk-space check shows ≥85% | Clean up disk space |
| Configuration generation failed | Script logs have genConfig ERROR | Check configuration template and parameters |
| Directory permission abnormal | Installation directory permissions not omm:ficommon 750 | Fix permissions |
| Data initialization failed | Component logs have init ERROR | Check data directory and initialization script |
| Dependency service not ready | Component logs have connection refused/timeout | Install/start dependency service first |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Installation target node |
| <oms_active_node> | common.md Phase 1 | OMS master node |
| <alarm_time> | Input parameter | Operation time |
| <instance_number> | Component config file | e.g., 1_3, 1_4 |
| <role> | Component config file | e.g., KerberosServer, DBServer |
