# Verification Method - MRS Fault Diagnosis

This document defines the verification steps for the MRS fault diagnosis skill. Verification is split into three levels: installation verification, configuration verification, and function verification.

> **Two modes**: this skill supports lakewatch mode (`lakewatch_api_client.py` + `fault_layer/` + `scenarios/` + `propagation.md`) and manager mode (`manager_api_client.py` + `fault_layer_manager/` + `scenarios_manager/` + `propagation_manager.md`). Run `python3 scripts/check_api_mode.py` to determine the active mode, then verify the corresponding client. The lakewatch-mode checks below apply to lakewatch mode; the manager-mode checks apply to manager mode.

## Level 1: Installation Verification

Verify Python and dependencies are installed.

| Check | Command | Success Criteria |
|-------|---------|------------------|
| Python version | `python3 --version` (Linux) / `python --version` (Windows) | >= 3.7 |
| `pyyaml` installed | `python3 -c "import yaml; print('ok')"` | Prints `ok` |
| `cryptography` installed (Windows only) | `python -c "import cryptography; print('ok')"` | Prints `ok` |
| Client scripts present | `ls scripts/lakewatch_api_client.py scripts/manager_api_client.py` | Both files exist |
| Config files present | `ls scripts/lakewatch_api_config.yaml scripts/manager_api_config.yaml` | Both files exist |
| Mode check script present | `ls scripts/check_api_mode.py` | File exists |

## Level 2: Configuration Verification

Verify the LakeWatch endpoint and credentials are configured.

| Check | Command | Success Criteria |
|-------|---------|------------------|
| Endpoint configured | Inspect `server.host` / `server.port` in `scripts/lakewatch_api_config.yaml` | Non-empty host and port |
| Account configured | Inspect `auth.username` / `auth.encrypted_password` in `scripts/lakewatch_api_config.yaml` | Non-empty username and ciphertext (NOT plaintext) |
| API catalog loads | `python3 scripts/lakewatch_api_client.py --list-apis` | Lists `collect_alarm_node_res_data`, `collect_alarm_log_data`, `access_manager_get`, `query-management-node-info`, etc. |
| No plaintext password | `grep -n "password:" scripts/lakewatch_api_config.yaml scripts/manager_api_config.yaml` | Only `encrypted_password` with ciphertext; no plaintext `password:` field |

### Manager Mode Configuration Verification

When `check_api_mode.py` reports `manager`, additionally verify:

| Check | Command | Success Criteria |
|-------|---------|------------------|
| Mode reported | `python3 scripts/check_api_mode.py` | JSON `{"mode": "manager", ...}` |
| Manager endpoint configured | Inspect `server.host` / `server.port` in `scripts/manager_api_config.yaml` | Non-empty floating IP and port 28443 |
| Manager account configured | Inspect `auth.username` / `auth.encrypted_password` in `scripts/manager_api_config.yaml` | Non-empty username and ciphertext (NOT plaintext) |
| Manager API catalog loads | `python3 scripts/manager_api_client.py --list-apis` | Lists `get_oms_info`, `get_host_process`, `get_instances`, `browse_log`, `start_log_search`, etc. |

## Level 3: Function Verification

Verify the LakeWatch API is callable end-to-end.

### 3.1 Token Acquisition (Implicit)

Token is auto-fetched on the first API call. A successful call in 3.2/3.3 implies token acquisition works.

### 3.2 Collect Node Resource Data

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

| Success Criteria | Description |
|------------------|-------------|
| HTTP 200 | Request succeeded |
| JSON with resource data | Response contains system-load metric data for the node |
| No `code:500` | Windows quoting is correct (no unescaped `"` in `-p` values) |

### 3.3 Collect Alarm Log Data

```bash
python3 scripts/lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'alarm_time=2026/06/11 16:00:32 GMT+08:00' \
  -p 'log_directory=/var/log/Bigdata/controller' \
  -p 'log_file_name=exe.log*' \
  -p 'keywords=["ERROR"]' \
  -p 'log_type=local'
```

| Success Criteria | Description |
|------------------|-------------|
| HTTP 200 | Request succeeded |
| JSON with log entries (or empty list if no match) | Log collection works |
| `alarm_time` accepted | Format `yyyy/MM/dd HH:mm:ss GMT+X:XX` is valid |

### 3.4 Proxy MRS Manager GET

```bash
python3 scripts/lakewatch_api_client.py -a access_manager_get \
  -p 'cluster_id=<cluster_id>' \
  -p 'target_url=api/v2/clusters/<cluster_id>/services'
```

| Success Criteria | Description |
|------------------|-------------|
| HTTP 200 | Request succeeded |
| JSON with service list | MRS Manager services returned |

### 3.5 Manager Mode Function Verification

When `check_api_mode.py` reports `manager`, verify the Manager API is callable end-to-end:

```bash
# Query OMS info (validates authentication + connectivity)
python3 scripts/manager_api_client.py -a get_oms_info --json

# Query host process status
python3 scripts/manager_api_client.py -a get_host_process \
  -p 'hostname=<node_name>' --json

# Query service instances
python3 scripts/manager_api_client.py -a get_instances \
  -p 'cluster_id=<cluster_id>' -p 'service_name=KrbServer' --json
```

| Success Criteria | Description |
|------------------|-------------|
| `get_oms_info` returns OMS info | Authentication and Manager connectivity work |
| `get_host_process` returns process list | Host process API works |
| `get_instances` returns instances | Instance API works |

## Diagnosis Flow Verification

After the environment is verified, confirm the diagnosis flow itself:

| Check | Method | Success Criteria |
|-------|--------|------------------|
| Component config exists | `ls components/KrbServer.md` | File exists |
| Component config is readable | Read `components/KrbServer.md` | Contains process, port, log path, etc. |
| Fault layer docs exist | `ls fault_layer/host_fault.md`, `ls fault_layer/instance_fault.md`, `ls fault_layer/service_fault.md` | All files exist |
| Manager fault layer docs exist | `ls fault_layer_manager/host_fault.md`, `ls fault_layer_manager/instance_fault.md`, `ls fault_layer_manager/service_fault.md` | All files exist |
| Scenario docs exist | `ls scenarios/common.md`, `ls scenarios/start.md`, etc. | All files exist |
| Manager scenario docs exist | `ls scenarios_manager/common.md`, `ls scenarios_manager/start.md`, etc. | All files exist |
| Propagation docs exist | `ls propagation.md propagation_manager.md` | Both files exist |
| Read-only constraint | Review all commands in the knowledge base | No start/stop/modify/delete commands |
| Placeholder substitution | Run a diagnosis with real values | No literal `<cluster_id>` / `<alarm_time>` in executed commands |
| Entry routing | Provide service_name only, node_name only, both | Correctly routes to service fault, host fault, instance fault entry |

## Verification Checklist

- [ ] Python >= 3.7 installed
- [ ] `pyyaml` (and `cryptography` on Windows) installed
- [ ] `lakewatch_api_config.yaml` has endpoint + account configured
- [ ] `--list-apis` returns the API catalog
- [ ] `collect_alarm_node_res_data` returns data
- [ ] `collect_alarm_log_data` returns data
- [ ] `access_manager_get` returns MRS Manager data
- [ ] (manager mode) `check_api_mode.py` reports `manager`
- [ ] (manager mode) `get_oms_info` / `get_host_process` / `get_instances` return data
- [ ] No plaintext password in config
- [ ] `components/<service_name>.md` exists for supported components
- [ ] `fault_layer/host_fault.md`, `instance_fault.md`, `service_fault.md` exist (lakewatch mode)
- [ ] `fault_layer_manager/host_fault.md`, `instance_fault.md`, `service_fault.md` exist (manager mode)
- [ ] `scenarios/common.md` and scenario-specific files exist (lakewatch mode)
- [ ] `scenarios_manager/common.md` and scenario-specific files exist (manager mode)
- [ ] `propagation.md` exists (lakewatch mode)
- [ ] `propagation_manager.md` exists (manager mode)
- [ ] All diagnosis commands are read-only
- [ ] Cross-skill dependency on huawei-cloud-mrs-host-alarm-diagnose declared in Prerequisites section 5
- [ ] Alarm document references point to `../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md` (lakewatch mode) or `alarm_manager/<alarm_id>.md` (manager mode)
