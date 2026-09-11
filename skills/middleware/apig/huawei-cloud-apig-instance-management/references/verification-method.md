# Verification Method

Each `huawei_*` action must be verified after execution. Read-only actions are
verified directly from the command output; mutating actions require a read-back
(回读) step that confirms the change.

## 1. Query actions (R3)

| Action | Verification |
|--------|--------------|
| `huawei_list_apig_instances` | JSON response contains `instances[]` with `id`, `status`, `eip_address` |
| `huawei_get_apig_instance` | Response contains exactly the requested `--instance_id`, `status != ""`. **Empty result (`total: 0`) means the instance does NOT exist** — report "实例不存在,请确认 instance_id", do not treat it as a successful query |
| `huawei_list_apig_api_groups` | Response contains `groups[]` with `id`, `name`, `sl_domain` |
| `huawei_list_apig_apis` | Response contains `apis[]` with `id`, `name`, `req_uri`, `auth_type` |
| `huawei_list_apig_throttling_policies` | Response contains `throttles[]` with `id`, `name`, `api_call_limits` |

```bash
hcloud APIG ListInstancesV2 --cli-region={region} --cli-output=json | jq '.instances[] | {id, name, status, eip_address}'
```

## 2. Analyze actions (R3)

| Action | Verification |
|--------|--------------|
| `huawei_analyze_apig_public_access` | Conclusion derived from `eip_address` (public) vs null (internal) vs `sl_domain` (internal-only); the report must state which address is safe for public use |
| `huawei_analyze_apig_publish_chain` | Chain walk completes at each hop: instance -> group -> API -> `publish_id`; missing hop is reported explicitly |

## 3. Manage actions (R2 — preview + confirm; then read-back)

| Action | Read-back verification |
|--------|------------------------|
| `huawei_create_apig_instance` | Poll `ListInstancesV2` until `status == "Running"` (5-15 min). Do NOT stop at `CreateSuccess`. |
| `huawei_add_apig_ingress_eip` | Confirm via the `AddIngressEipV2` response/task acceptance, a retry returning `APIC.7711` ("Public inbound access is enabled"), or the EIP list in the APIG console. **Do NOT rely on `ListInstancesV2` `eip_address` as the sole evidence** — it can remain `null` for 8+ minutes after success |
| `huawei_create_apig_api_group` | `ListApiGroupsV2 --instance_id` contains the new group (match by name/id); capture `sl_domain` |
| `huawei_create_apig_api` | `ListApisV2 --instance_id --group_id` contains the new API. **Known limitation:** with KooCLI 7.2.12 an HTTP backend (`--backend_type=HTTP`) fails with APIG.2011 — use `MOCK`/`FUNCTION` backend or the console for HTTP backends |
| `huawei_update_apig_api` | `ListApisV2` shows the updated fields (path, auth mode, etc.) |
| `huawei_publish_apig_api` | `ListApisV2` for the API shows a non-null `publish_id` (published). **`--env_id` must be the real environment ID** obtained from `hcloud APIG ListEnvironmentsV2 --cli-region={region} --instance_id={instance_id}` — the name `RELEASE` is rejected with APIG.3003 |
| `huawei_create_apig_throttling_policy` | `ListRequestThrottlingPolicyV2 --instance_id` contains the new policy |

## 4. Delete actions (R1 — explicit confirm; then confirm removal)

| Action | Verification |
|--------|--------------|
| `huawei_delete_apig_instance` | `ListInstancesV2 --instance_id` returns empty / instance gone (deletion is async; poll until absent) |
| `huawei_delete_apig_api` | `ListApisV2 --instance_id --group_id` no longer contains the API id |
| `huawei_delete_apig_api_group` | `ListApiGroupsV2 --instance_id` no longer contains the group id. **Group must be empty first**: delete every API in it via `huawei_delete_apig_api` (`DeleteApiV2`), otherwise APIG rejects the deletion (`APIG.3415` — group contains APIs) |

## 5. General rules

1. Always pass `--cli-output=json` when the result is consumed programmatically (e.g. with `jq`).
2. Before running any operation, confirm parameter names with `hcloud APIG <Operation> --help`.
3. Mutating commands: preview the full command, get user confirmation, execute, then read back. Never skip the read-back.
4. If a read-back fails, return the error and do not claim success.