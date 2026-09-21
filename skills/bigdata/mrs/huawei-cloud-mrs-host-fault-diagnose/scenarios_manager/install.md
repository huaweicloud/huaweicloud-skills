# Install Scenario Diagnosis (install)

> Prerequisites: The common check phases 1-5 of common.md have been completed
> Component config: load `components/<service_name>.md` to obtain component information

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
python manager_api_client.py -a browse_log \
  -p 'hostname=<oms_active_node>' \
  -p 'file_name=/var/log/Bigdata/controller/exe.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

**Common Problems**:

| ERROR Keyword | Possible Cause | Repair Suggestion |
|---------------|---------------|-------------------|
| Package not found | Package not distributed to the node | Check the packages directory and re-distribute |
| Extract failed | Insufficient disk space or corrupted package | Clean up disk, verify SHA256 |
| Permission denied | Abnormal distribution directory permission | Check /opt/huawei/Bigdata/packages permissions |
| Checksum mismatch | Corrupted installation package | Re-download the installation package |

---

## Step 2: Configuration File Generation Check

Check the NodeAgent script logs for errors related to configuration generation:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

Also check whether the configuration file was generated under the component instance directory:
- Check path: `$BIGDATA_HOME/FusionInsight_Current/<instance_id>_<rolename>/etc/`
- Check file: whether configurations.xml exists

---

## Step 3: Directory Permission and Data Initialization Check

### 3.1 Installation Directory Permission Check

Check the NodeAgent script logs for errors related to directory permission, and confirm the installation directory permissions are correct:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

> **Note**: The LakeWatch API has no direct strategy to check file permissions. Determine indirectly through permission-related keywords in the script logs.

### 3.2 Data Directory Initialization

For components with data directories (such as DBService's `/srv/BigData/dbdata_service/data`),
check whether the data directory has been correctly initialized.

Check the NodeAgent script logs for initialization-related content:

```bash
python manager_api_client.py -a browse_log \
  -p 'hostname=<node_name>' \
  -p 'file_name=/var/log/Bigdata/nodeagent/scriptlog/script.log' \
  -p 'start_line=1' \
  -p 'end_line=500' \
  -p 'search=<service_name>' --json
```

---

## Step 4: Post-Install Verification

### 4.1 Process and Port Verification

After install, the component normally starts automatically; check the process and port according to common.md Phase 4.

### 4.2 Component-Specific Verification

Refer to the check items in the `Scenario-Specific Check Points > Install (install)` section of the component config file,
load the component config and execute each check item.

For each check item, choose the appropriate API call based on the check content it describes:
- Process/port check → `get_host_process`
- Log check → `browse_log` / `start_log_search`
- HA status → `get_instances`

---

## Common Root Causes and Repair Suggestions

| Root Cause | Characteristic | Repair Suggestion |
|------------|---------------|-------------------|
| Installation package missing or corrupted | Controller log has Package not found | Re-distribute the installation package, verify SHA256 |
| Insufficient disk space | disk-space check shows ≥85% | Clean up disk space |
| Configuration generation failed | Script log has genConfig ERROR | Check the config template and parameters |
| Abnormal directory permission | Install directory permission is not omm:ficommon 750 | Fix the permissions |
| Data initialization failed | Component log has init ERROR | Check the data directory and initialization script |
| Dependency service not ready | Component log has connection refused/timeout | Install/start the dependency service first |

## Variable Description

| Variable | Source | Description |
|----------|--------|-------------|
| <cluster_id> | Input parameter | Cluster ID |
| <service_name> | Input parameter | Component service name |
| <node_name> | Input parameter | Installation target node |
| <oms_active_node> | common.md Phase 1 | OMS primary node |
| <alarm_time> | Input parameter | Operation time |
| <instance_id> | Component config file | Such as 1_3, 1_4 |
| <rolename> | Component config file | Such as KerberosServer, DBServer |
