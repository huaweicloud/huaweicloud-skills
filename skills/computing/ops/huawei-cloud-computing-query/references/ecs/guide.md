# ECS Query Guide

All ECS queries go through one entry: `.venv/bin/python3 scripts/huawei_ecs.py <subcommand> [options]`.
Every subcommand supports `--region` (default `HW_REGION_NAME` or `cn-north-4`), `--project_id`
(auto-resolved through IAM when omitted) and `--json`.

## Subcommands

| Subcommand | Purpose |
|------------|---------|
| `list_servers_details` | ECS instance list with flavor, charging mode and optional related resources |
| `list_cloud_servers` | Cloud server list including image and flavor summary |
| `list_servers_details_by_id` | Instance details for one instance ID |
| `list_flavors` | Flavor list (available by default) |
| `list_flavor_sell_policies` | Flavor sell policies |
| `list_resize_flavors` | Flavors available for resize |
| `list_server_az_info` | Availability zone information |
| `list_server_groups` | Server group list |
| `show_server_group` | Server group details |
| `list_server_block_devices` | Block devices of one server |
| `show_server_block_device` | One block device |
| `list_server_interfaces` | NICs of one server |
| `nova_show_server_interface` | One NIC |
| `list_server_volume_attachments` | Attached volumes |
| `list_server_tags` | Project tag list |
| `show_server_tags` | Tags of one server |
| `list_servers_by_tag` | Servers filtered by tag |
| `list_templates` | Launch templates |
| `list_launch_template_versions` | Launch template versions |
| `list_recycle_bin_servers` | Recycle bin servers |
| `show_recycle_bin` | Recycle bin configuration |
| `list_scheduled_events` | Scheduled events |
| `show_server` | Server details |
| `show_server_limits` | Tenant quota |
| `show_server_password` | Server password |
| `show_server_remote_console` | VNC console address |
| `show_serial_console_actions` | Serial console address |
| `show_server_attachable_nic_num` | Attachable NIC count |
| `show_appendable_volume_quota` | Appendable volume quota |
| `show_flavor_capacity` | Flavor capacity |
| `nova_list_keypairs` | SSH keypair list |
| `nova_show_keypair` | SSH keypair details |
| `nova_list_server_security_groups` | Security groups of one server |
| `nova_show_flavor_extra_specs` | Flavor extra specs |
| `show_metadata_options` | Metadata options |
| `show_reset_password_flag` | Password reset flag |
| `show_job` | Async job status |

## Common options

| Option | Applies to | Meaning |
|--------|------------|---------|
| `--region <region>` | all | Region; falls back to `HW_REGION_NAME` |
| `--project_id <id>` | all | Project ID; resolved through IAM when omitted |
| `--limit <n>` | list | Rows displayed, default 20 |
| `--all` | list | Fetch every page and display all rows |
| `--fields id,name,status` | list/show | Display only these comma-separated fields |
| `--json` | all | Raw JSON output |
| `--tag key=value` | list | Repeatable tag filter (AND) |
| `--not_tag key=value` | list | Repeatable tag exclusion (AND) |
| `--with_related` | `list_servers_details`, `show_server` | Add fixed IPs, floating IPs, security groups and volumes |

## Example

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_ecs.py show_server --region cn-north-4 --server_id "<server_id>"
```

## Pagination and output

- Default output is a compact table of `id`, `name` and `status`, at most 20 rows, plus `共 N 条，当前返回 M 条`.
- Use `--fields` to choose columns and `--all` to walk all pages.
- `--with_related` adds `fixed_ips`, `floating_ips`, `security_groups` and `volumes` columns; all values come from the same list response, no extra API call.
- Empty results print the region and a short diagnostic hint instead of an empty table.

## Migrating from old script paths

| Old path | New command |
|----------|-------------|
| `scripts/ecs/list_servers_details.py` | `scripts/huawei_ecs.py list_servers_details` |
| `scripts/ecs/list_cloud_servers.py` | `scripts/huawei_ecs.py list_cloud_servers` |
| `scripts/ecs/show_server.py` | `scripts/huawei_ecs.py show_server` |
| `scripts/ecs/list_flavors.py` | `scripts/huawei_ecs.py list_flavors` |
| `scripts/ecs/<operation>.py` | `scripts/huawei_ecs.py <operation>` |

The subcommand name always equals the old script file name without the `.py` suffix.
