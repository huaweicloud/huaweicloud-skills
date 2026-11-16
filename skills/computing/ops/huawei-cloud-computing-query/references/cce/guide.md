# CCE Query Guide

All CCE queries are read-only and go through one entry: `.venv/bin/python3 scripts/huawei_cce.py <subcommand> [options]`.
Every subcommand supports `--region` (default `HW_REGION_NAME` or `cn-north-4`), `--project_id`
(auto-resolved through IAM when omitted) and `--json`.

## Subcommands

| Subcommand | Purpose |
|------------|---------|
| `list_clusters` | Cluster list (`ListClusters`) |
| `show_cluster` | Cluster details (`ShowCluster`) |
| `list_nodes` | Node list with automatic pagination (`ListNodes`) |
| `show_node` | Node details (`ShowNode`) |
| `list_node_pools` | Node pool list (`ListNodePools`) |
| `show_node_pool` | Node pool details (`ShowNodePool`) |
| `show_cluster_tags` | Cluster tags (`GetResourceTags`) |
| `list_node_pools_by_tag` | Node pools filtered by tag or label |
| `show_quota` | CCE quota (`ShowQuotas`) |

## Common options

| Option | Applies to | Meaning |
|--------|------------|---------|
| `--region <region>` | all | Region; falls back to `HW_REGION_NAME` |
| `--project_id <id>` | all | Project ID; resolved through IAM when omitted |
| `--cluster_id <id>` | cluster-scoped queries | Cluster ID |
| `--limit <n>` | list | Rows displayed, default 20 |
| `--all` | list | Fetch every page and display all rows |
| `--fields id,name,status` | list/show | Display only these comma-separated fields |
| `--json` | all | Raw JSON output |
| `--detail true` | `list_clusters` | Include cluster detail section |
| `--show_default_node_pool true` | `list_node_pools` | Include the default node pool |
| `--advance_status true` | node pool queries | Include advanced status |

## Example

```bash
.venv/bin/python3 scripts/huawei_cce.py list_clusters --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_cce.py list_nodes --region cn-north-4 --cluster_id "<cluster_id>" --all
```

```bash
.venv/bin/python3 scripts/huawei_cce.py show_node_pool --region cn-north-4 --cluster_id "<cluster_id>" --nodepool_id "<nodepool_id>"
```

## Output

- Cluster and node rows expose `id`, `name` and `status`, at most 20 rows by default, plus `共 N 条，当前返回 M 条`.
- `--all` walks every page; on large clusters prefer `--fields` to keep the answer compact.
- Empty results include the region, project and a troubleshooting hint instead of a blank table.
- CCE v3 exposes no read API for cluster certificates; use the console when certificate status is required.

## Out of scope

Workloads, namespaces, events and pod logs belong to the kubectl-based `container/cce/` skills.
Node pool resize and other write operations belong to the CCE cluster management skill.

## Migrating from old script paths

| Old path | New command |
|----------|-------------|
| `scripts/cce/list_clusters.py` | `scripts/huawei_cce.py list_clusters` |
| `scripts/cce/list_nodes.py` | `scripts/huawei_cce.py list_nodes` |
| `scripts/cce/show_node_pool.py` | `scripts/huawei_cce.py show_node_pool` |
| `scripts/cce/<operation>.py` | `scripts/huawei_cce.py <operation>` |

The subcommand name always equals the old script file name without the `.py` suffix.
