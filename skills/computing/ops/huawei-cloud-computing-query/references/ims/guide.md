# IMS Query Guide

All IMS queries go through one entry: `.venv/bin/python3 scripts/huawei_ims.py <subcommand> [options]`.
Every subcommand supports `--region` (default `HW_REGION_NAME` or `cn-north-4`), `--project_id`
(auto-resolved through IAM when omitted) and `--json`.

## Subcommands

| Subcommand | Purpose |
|------------|---------|
| `list_images` | Image list with OS, status and visibility |
| `list_image_by_tags` | Images filtered by tags |
| `list_image_members` | Members of one image |
| `show_image_member` | One member of one image |
| `list_image_tags` | Tags of one image |
| `list_images_tags` | All image tags of the tenant |
| `list_tags` | Tenant image tag list |
| `list_os_versions` | OS versions supported by images |
| `show_image` | Image details |
| `show_image_quota` | Image quota |
| `show_job` | Async job information |
| `show_job_progress` | Async job progress |

## Common options

| Option | Applies to | Meaning |
|--------|------------|---------|
| `--region <region>` | all | Region; falls back to `HW_REGION_NAME` |
| `--project_id <id>` | all | Project ID; resolved through IAM when omitted |
| `--limit <n>` | list | Rows displayed, default 20 |
| `--all` | list | Fetch every page and display all rows |
| `--fields id,name,status` | list/show | Display only these comma-separated fields |
| `--json` | all | Raw JSON output |
| `--imagetype gold` | `list_images` | gold, private, shared or market |
| `--os_type Linux` | `list_images` | Linux, Windows or Other |

## Example

```bash
.venv/bin/python3 scripts/huawei_ims.py list_images --region cn-north-4 --os_type Linux --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_ims.py show_image --region cn-north-4 --image_id "<image_id>"
```

## Output

- List output prints `id`, `name` and `status`, at most 20 rows by default, plus `共 N 条，当前返回 M 条`.
- Use `--all` for the full inventory and `--fields` for a custom column set.
- Empty results include the region and a short diagnostic hint.

## Migrating from old script paths

| Old path | New command |
|----------|-------------|
| `scripts/ims/list_images.py` | `scripts/huawei_ims.py list_images` |
| `scripts/ims/show_image.py` | `scripts/huawei_ims.py show_image` |
| `scripts/ims/<operation>.py` | `scripts/huawei_ims.py <operation>` |

The subcommand name always equals the old script file name without the `.py` suffix.
