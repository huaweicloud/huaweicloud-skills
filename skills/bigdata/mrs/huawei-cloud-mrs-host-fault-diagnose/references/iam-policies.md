# IAM Policies - MRS Fault Diagnosis

This skill does NOT use Huawei Cloud IAM AK/SK or KooCLI. It authenticates either to the LakeWatch service with a LakeWatch account (username + encrypted password) and accesses MRS cluster data through the LakeWatch API, or directly to the MRS Manager REST API with a Manager account (manager mode). This document describes the access model and the required roles/permissions.

## Access Architecture

```
Caller (Agent) -> check_api_mode.py -> lakewatch_api_client.py -> LakeWatch API -> MRS cluster
                                                        -> MRS Manager (proxy via manager-access)
Caller (Agent) -> check_api_mode.py -> manager_api_client.py -> MRS Manager REST API (28443)
```

- **LakeWatch authentication**: username + encrypted password (CryptoAPI on Linux, AES-256-CBC on Windows). Token is auto-fetched and cached locally.
- **MRS Manager authentication (manager mode)**: username + encrypted password (Basic Auth or Cookie/JSESSIONID) against the Manager floating IP port 28443.
- **MRS data access**: granted by the LakeWatch service account or the MRS Manager account; no direct Huawei Cloud IAM AK/SK is involved.

## Required LakeWatch Account Permissions

The LakeWatch account configured in `scripts/lakewatch_api_config.yaml` (`auth.username`) must be able to call the following APIs on the target MRS cluster:

| API Name | Purpose | Required For |
|----------|---------|--------------|
| `get_token` | Obtain the authentication token (built-in, auto-called) | All calls |
| `collect_alarm_node_res_data` | Collect alarm node resource data (CPU, memory, disk, network, process, etc.) | Resource diagnosis |
| `collect_alarm_log_data` | Collect alarm-related log data around the fault time | Log diagnosis |
| `access_manager_get` | Proxy MRS Manager GET API (cluster info, services, hosts, alarms, etc.) | Manager-side diagnosis |
| `query-node-ip` | Query the node IP by node name | Node resolution |
| `query-management-node-info` | Query the cluster primary/standby node names | HA diagnosis |

## MRS Manager Permissions (via LakeWatch Proxy)

When the skill calls `access_manager_get` to proxy MRS Manager GET endpoints, the underlying MRS Manager account (used by LakeWatch) needs read access to:

| MRS Manager Resource | Purpose | Example target_url |
|----------------------|---------|--------------------|
| Cluster info | Get cluster basic information | `api/v2/clusters` |
| Cluster services | Get service list and status | `api/v2/clusters/<cluster_id>/services` |
| Host processes | Get processes on a specific host | `api/v2/clusters/<cluster_id>/hosts/<node_name>/processes` |
| Service instances | Get instances of a specific service | `api/v2/clusters/<cluster_id>/services/<service_name>/instances` |
| Active alarms | Check for active alarms on the cluster | `api/v2/clusters/<cluster_id>/alarms` |
| Host info | Check host status and operational state | `api/v2/clusters/<cluster_id>/hosts?hostName=<node_name>` |

> `target_url` MUST NOT start with `/`. The proxy only supports GET. PUT is not yet available on the Agent side.

## MRS Manager Permissions (Manager Mode)

In manager mode, the skill calls the MRS Manager REST API directly through `manager_api_client.py`. The Manager account configured in `scripts/manager_api_config.yaml` (`auth.username`) needs read access to:

| MRS Manager API | Purpose | manager_api_client API |
|-----------------|---------|------------------------|
| OMS info | Query OMS primary/standby nodes | `get_oms_info` |
| Host info | Query host detail (disk/memory/CPU) | `get_host_detail`, `get_hosts` |
| Host process | Confirm whether a process exists on a host | `get_host_process` |
| Host metrics | View monitor metrics (`dev_` prefix) | `get_host_metrics` |
| Instance status | Query service instance running/HA status | `get_instances` |
| Service status | Query cluster services | `get_cluster_services` |
| Alarm list | Query active alarms and accompanying alarms | `get_alarms` |
| Remote connectivity | Check whether a remote node is reachable | `check_remote` |
| Log search/browse | Search logs by keyword or browse log files | `start_log_search`, `get_log_search_progress`, `browse_log` |

> The Manager account needs at least read-only (view) permissions on OMS, host, instance, service, alarm, and log modules. See [MRS Manager API Client](manager-api-client.md) for the full API catalog.

## Huawei Cloud IAM (Not Directly Required)

This skill does not call Huawei Cloud public APIs directly, so no Huawei Cloud IAM AK/SK policy is required to run the skill itself. If the deployment environment uses an ECS IAM role to reach the LakeWatch endpoint, ensure the ECS instance has network access to the LakeWatch service host/port configured in `lakewatch_api_config.yaml`.

## Permission Failure Handling

1. When an API call fails with an authentication error (401) or permission error (403), read this document.
2. Determine the current mode with `check_api_mode.py`:
   - **Lakewatch mode**: display the required LakeWatch account permissions and MRS Manager proxy resources to the user.
   - **Manager mode**: display the required MRS Manager account permissions to the user.
3. Guide the user to confirm the corresponding account has the required permissions on the target cluster.
4. Pause execution and wait for the user to confirm permissions are granted.

## Common Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| 401 Unauthorized | LakeWatch/Manager account credentials invalid or expired | Re-encrypt the password with `--encrypt-password`; verify the username |
| 403 Forbidden | Account lacks permission on the target cluster | Grant the account access to the target MRS cluster |
| Connection timeout | LakeWatch endpoint or Manager port 28443 unreachable | Check host/port and network connectivity |
| `50201` / `RDS.9999` | LakeWatch / Autopilot backend unavailable | Retry later or contact operations |
| Agent version too low | `access_manager_get` not supported | Upgrade LakeWatch Agent to >= 1.0.5 and ensure OMS node info is reported |
| Manager login failure | Wrong Manager password or wrong floating IP | Re-run `manager_api_client.py --encrypt-password`; verify `server.host` is the Manager floating IP |
