# BMS Query Guide

All BMS queries go through one entry: `.venv/bin/python3 scripts/huawei_bms.py <subcommand> [options]`.
Every subcommand supports `--region` (default `HW_REGION_NAME` or `cn-north-4`), `--project_id`
(auto-resolved through IAM when omitted) and `--json`.

## Subcommands

| Subcommand | Purpose |
|------------|---------|
| `list_bare_metal_servers` | Bare metal server list with total count |
| `list_bare_metal_servers_detail` | Bare metal server detail list without total count |
| `list_bare_metal_server_details` | One bare metal server by ID |
| `list_baremetal_flavor_detail_extends` | Bare metal flavor details |
| `show_available_resource` | Available resources for an AZ and flavor |
| `show_baremetal_server_interface_attachments` | NICs of one server |
| `show_baremetal_server_tags` | Tags of one server |
| `show_baremetal_server_volume_info` | Attached disks of one server |
| `show_metadata_options` | Metadata options |
| `show_reset_pwd` | Password reset support flag |
| `show_server_remote_console` | VNC console address |
| `show_tenant_quota` | Tenant quota |
| `show_windows_baremetal_server_pwd` | Windows initial password |
| `show_job_infos` | Async job status |
| `show_specified_version` | BMS API version details |

## Common options

| Option | Applies to | Meaning |
|--------|------------|---------|
| `--region <region>` | all | Region; falls back to `HW_REGION_NAME` |
| `--project_id <id>` | all | Project ID; resolved through IAM when omitted |
| `--limit <n>` | list | Rows displayed, default 20 |
| `--all` | list | Fetch every page and display all rows |
| `--fields id,name,status` | list/show | Display only these comma-separated fields |
| `--json` | all | Raw JSON output |

## Example

```bash
.venv/bin/python3 scripts/huawei_bms.py list_bare_metal_servers --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_bms.py show_tenant_quota --region cn-north-4
```

## Output

- List output prints `id`, `name` and `status`, at most 20 rows by default, plus `共 N 条，当前返回 M 条`.
- Show output prints one `field: value` per line; use `--fields` to limit the lines.
- Empty results include the region and a short diagnostic hint.

## Migrating from old script paths

| Old path | New command |
|----------|-------------|
| `scripts/bms/list_bare_metal_servers.py` | `scripts/huawei_bms.py list_bare_metal_servers` |
| `scripts/bms/show_tenant_quota.py` | `scripts/huawei_bms.py show_tenant_quota` |
| `scripts/bms/<operation>.py` | `scripts/huawei_bms.py <operation>` |

The subcommand name always equals the old script file name without the `.py` suffix.
