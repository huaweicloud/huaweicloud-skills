# AS Query Guide

All Auto Scaling queries go through one entry: `.venv/bin/python3 scripts/huawei_as.py <subcommand> [options]`.
Every subcommand supports `--region` (default `HW_REGION_NAME` or `cn-north-4`), `--project_id`
(auto-resolved through IAM when omitted) and `--json`.

## Subcommands

| Subcommand | Purpose |
|------------|---------|
| `list_scaling_groups` | Scaling group list |
| `show_scaling_group` | Scaling group details |
| `list_scaling_configs` | Scaling configuration list |
| `show_scaling_config` | Scaling configuration details |
| `list_scaling_instances` | Instances in one scaling group |
| `list_scaling_policies` | Scaling policies (v1) |
| `show_scaling_policy` | Scaling policy details (v1) |
| `list_scaling_v2_policies` | Scaling policies (v2) |
| `show_scaling_v2_policy` | Scaling policy details (v2) |
| `list_all_scaling_v2_policies` | All scaling and bandwidth policies (v2) |
| `list_scaling_activity_logs` | Activity logs (v1) |
| `list_scaling_activity_v2_logs` | Activity logs (v2) |
| `list_scaling_policy_execute_logs` | Policy execution logs |
| `list_scaling_notifications` | SMN notifications of one group |
| `list_life_cycle_hooks` | Lifecycle hooks of one group |
| `show_life_cycle_hook` | Lifecycle hook details |
| `list_hook_instances` | Instances waiting in a lifecycle hook |
| `list_group_scheduled_tasks` | Scheduled tasks of one group |
| `list_warm_pool_instances` | Warm pool instances |
| `list_warm_pool_instances_new` | Warm pool instances (new API) |
| `show_warm_pool` | Warm pool configuration |
| `show_warm_pool_new` | Warm pool configuration (new API) |
| `show_resource_quota` | AS resource quota |
| `show_policy_and_instance_quota` | Policy and instance quota of one group |
| `list_scaling_tag_infos_by_resource_id` | Tags of one resource |
| `list_scaling_tag_infos_by_tenant_id` | Tags of all resources |
| `list_resource_instances` | Resource instances by resource type |
| `list_api_versions` | AS API versions |
| `show_api_version` | AS API version details |

## Common options

| Option | Applies to | Meaning |
|--------|------------|---------|
| `--region <region>` | all | Region; falls back to `HW_REGION_NAME` |
| `--project_id <id>` | all | Project ID; resolved through IAM when omitted |
| `--limit <n>` | list | Rows displayed, default 20 |
| `--all` | list | Fetch every page and display all rows |
| `--fields id,name,status` | list/show | Display only these comma-separated fields |
| `--json` | all | Raw JSON output |
| `--scaling_group_id <id>` | group-scoped queries | Scaling group ID |
| `--start_number <n>` | list | Server-side start row |
| `--offset <n>` | list | Client-side display offset |

## Example

```bash
.venv/bin/python3 scripts/huawei_as.py list_scaling_groups --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_as.py show_scaling_group --region cn-north-4 --scaling_group_id "<scaling_group_id>"
```

## Output

- List output prints the first summary fields (group ID, name and status when available), at most 20 rows by default.
- Use `--all` for the full inventory and `--fields` for a custom column set.
- Empty results include the region and a short diagnostic hint.

## Migrating from old script paths

| Old path | New command |
|----------|-------------|
| `scripts/as/list_scaling_groups.py` | `scripts/huawei_as.py list_scaling_groups` |
| `scripts/as/show_scaling_group.py` | `scripts/huawei_as.py show_scaling_group` |
| `scripts/as/<operation>.py` | `scripts/huawei_as.py <operation>` |

The subcommand name always equals the old script file name without the `.py` suffix.
