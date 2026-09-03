# IAM Policies - MRS Fault Diagnosis

This skill does NOT use Huawei Cloud IAM AK/SK or KooCLI. It authenticates to the LakeWatch service with a LakeWatch account (username + encrypted password) and accesses MRS cluster data through the LakeWatch API. This document describes the access model and the required roles/permissions.

## Access Architecture

```
Caller (Agent) -> lakewatch_api_client.py -> LakeWatch API -> MRS cluster
                                                       -> MRS Manager (proxy via manager-access)
```

- **LakeWatch authentication**: username + encrypted password (CryptoAPI on Linux, AES-256-CBC on Windows). Token is auto-fetched and cached locally.
- **MRS data access**: granted by the LakeWatch service account; no direct Huawei Cloud IAM AK/SK is involved.

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

## Huawei Cloud IAM (Not Directly Required)

This skill does not call Huawei Cloud public APIs directly, so no Huawei Cloud IAM AK/SK policy is required to run the skill itself. If the deployment environment uses an ECS IAM role to reach the LakeWatch endpoint, ensure the ECS instance has network access to the LakeWatch service host/port configured in `lakewatch_api_config.yaml`.

## Permission Failure Handling

1. When a LakeWatch API call fails with an authentication error (401) or permission error (403), read this document.
2. Display the required LakeWatch account permissions and MRS Manager proxy resources to the user.
3. Guide the user to confirm the LakeWatch account has the required permissions on the target cluster.
4. Pause execution and wait for the user to confirm permissions are granted.

## Common Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| 401 Unauthorized | LakeWatch account credentials invalid or expired | Re-encrypt the password with `--encrypt-password`; verify `auth.username` |
| 403 Forbidden | LakeWatch account lacks permission on the target cluster | Grant the account access to the target MRS cluster |
| Connection timeout | LakeWatch endpoint unreachable | Check `server.host`/`port` and network connectivity |
| `50201` / `RDS.9999` | LakeWatch / Autopilot backend unavailable | Retry later or contact operations |
| Agent version too low | `access_manager_get` not supported | Upgrade LakeWatch Agent to >= 1.0.5 and ensure OMS node info is reported |
