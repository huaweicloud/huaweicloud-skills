# ECS Python Script Usage Guide

---

## List Query Scripts

### list_servers_details.py — Query ECS Instance List

Purpose: Query the list of ECS instances, including ID, name, status, charging_mode, flavor_id, vCPU, memory(GiB).
Usage: python scripts/ecs/list_servers_details.py -h

Key options:

- `--tag key=value`：按标签过滤，可重复指定，多个标签之间为 AND 关系，最终拼成 ECS API 的 `tags` 查询参数（格式 `key1=value1,key2=value2`）。
- `--not_tag key=value`：按标签排除，可重复指定，多个标签之间为 AND 关系，对应 API 的 `not_tags` 查询参数。
- `--export csv|json`：把本次查询结果导出为文件；CSV 使用 UTF-8-SIG 编码，Excel 可直接打开。
- `--export_path <file>`：导出文件路径；不传时默认写入当前目录 `<脚本名>_<时间戳>.<格式>`，例如 `list_servers_details_20261102_194203.csv`。
- 导出内容包含表格展示字段（id/name/status/charging_mode/flavor_id/vcpus/memory(GiB)/availability_zone/created），并额外包含首个 IPv4 地址 `ip`；导出完成后打印 `已导出 N 条到 <文件> (格式: ...)`。

输出中的 `charging_mode` 来源于实例 `metadata.charging_mode`，取值映射为 `0`→按需、`1`→包周期、`2`→竞价；空值显示 `-`，未知值原样透出。

示例：

```bash
python scripts/ecs/list_servers_details.py --region cn-north-4 --tag env=prod --tag group=web
python scripts/ecs/list_servers_details.py --region cn-north-4 --not_tag env=test --export csv --export_path ./servers.csv
python scripts/ecs/list_servers_details.py --region cn-north-4 --tag owner=alice --export json
```

注意：原有的 `--tags` / `--not_tags`（查询 tag 字段中包含 / 不包含该值的云服务器）语义不同，为保持兼容未做改动；`--tag` / `--not_tag` 不能与它们同时使用，同时指定会直接报错退出。查询结果为空时不生成导出文件。分页上限见文末「分页上限与翻页语义」。

---

### list_servers_details_by_id.py — Query ECS Details by Instance ID

Purpose: Query ECS instance details, including name, status, flavor_id, vCPU, memory(GiB).
Usage: python scripts/ecs/list_servers_details_by_id.py -h

---

### list_cloud_servers.py — Query Cloud Server List (v1.1)

Purpose: Query the list of ECS cloud servers, including name, status, charging_mode, flavor_id, vCPU, ram(GiB), image ID.
Usage: python scripts/ecs/list_cloud_servers.py -h

Key options:

- `--tag key=value`：按标签过滤，可重复指定，多个标签之间为 AND 关系，最终拼成 ECS API 的 `tags` 查询参数（格式 `key1=value1,key2=value2`）。
- `--not_tag key=value`：按标签排除，可重复指定，多个标签之间为 AND 关系，对应 API 的 `not_tags` 查询参数。
- `--charging_mode 0|1|2`：按计费类型过滤（0-按需，1-包周期，2-竞价），仅筛选不改变输出列；输出列始终展示 `charging_mode`。
- `--export csv|json`：把本次查询结果导出为文件；CSV 使用 UTF-8-SIG 编码，Excel 可直接打开。
- `--export_path <file>`：导出文件路径；不传时默认写入当前目录 `<脚本名>_<时间戳>.<格式>`，例如 `list_cloud_servers_20261102_194203.json`。
- 导出内容包含表格展示字段（id/name/status/charging_mode/flavor_id/vcpus/ram(GiB)/availability_zone/created），并额外包含首个 IPv4 地址 `ip`；指定 `--expect_fields image` 时还会导出 `image_id`。导出完成后打印 `已导出 N 条到 <文件> (格式: ...)`。

输出中的 `charging_mode` 来源于实例 `metadata.charging_mode`。该接口的 `metadata` 属非默认返回字段，脚本会自动将其并入 `--expect_fields` 一并请求（与用户传入值求并集），取值映射为 `0`→按需、`1`→包周期、`2`→竞价；空值显示 `-`，未知值原样透出。

示例：

```bash
python scripts/ecs/list_cloud_servers.py --region cn-north-4 --tag env=prod --tag group=web
python scripts/ecs/list_cloud_servers.py --region cn-north-4 --not_tag env=test --export csv --export_path ./servers.csv
python scripts/ecs/list_cloud_servers.py --region cn-north-4 --tag env=prod --export json
```

注意：原有的 `--tags` / `--not_tags`（查询 tag 字段中包含 / 不包含该值的云服务器）语义不同，为保持兼容未做改动；`--tag` / `--not_tag` 不能与它们同时使用，同时指定会直接报错退出。查询结果为空时不生成导出文件。分页上限见文末「分页上限与翻页语义」。

---

### list_flavors.py — Query ECS Flavor List

Purpose: Query the list of ECS flavors, including flavor name, vCPU, memory(GiB).
Usage: python scripts/ecs/list_flavors.py -h

**Important:** By default only available flavors are returned (deprecated and sold-out flavors filtered out via sell policies cross-reference). Use `--only_available false` to see all flavor definitions including deprecated ones. The flag accepts `true` (default) or `false`; omitting it or passing `--only_available` alone both default to `true`.

---

### list_flavor_sell_policies.py — Query Flavor Sell Policies

Purpose: Query the list of ECS flavor sell policies, including ID, flavor_id, sell mode, sell status, availability_zone_id.
Usage: python scripts/ecs/list_flavor_sell_policies.py -h

---

### list_resize_flavors.py — Query Resize Flavor List

Purpose: Query the list of ECS resize flavors, including flavor_id, name, vCPU, ram(GiB).
Usage: python scripts/ecs/list_resize_flavors.py -h

---

### list_server_az_info.py — Query Availability Zone List

Purpose: Query the list of ECS availability zone information, including availability_zone_id and type.
Usage: python scripts/ecs/list_server_az_info.py -h

---

### list_server_block_devices.py — Query Server Block Device List Details

Purpose: Query the list of ECS server block devices, including cloud disk ID, boot_index, device, size(GB).
Usage: python scripts/ecs/list_server_block_devices.py -h

---

### list_server_groups.py — Query Server Group List

Purpose: Query the list of ECS server groups, including ID, name, policy.
Usage: python scripts/ecs/list_server_groups.py -h

---

### list_server_interfaces.py — Query Server Network Interface Information

Purpose: Query the list of ECS server network interfaces, including port ID, network ID, ip_addr, mac_addr.
Usage: python scripts/ecs/list_server_interfaces.py -h

---

### list_server_tags.py — Query Project Tags

Purpose: Query the list of ECS server tags, including key and values.
Usage: python scripts/ecs/list_server_tags.py -h

---

### list_server_volume_attachments.py — Query Server Volume Attachment List

Purpose: Query the list of ECS server volume attachments, including ID, device, server ID, cloud disk ID.
Usage: python scripts/ecs/list_server_volume_attachments.py -h

---

### list_servers_by_tag.py — Query Server List by Tag

Purpose: Query the list of ECS servers by tag, including resource ID, resource name, and tags.
Usage: python scripts/ecs/list_servers_by_tag.py -h

---

### list_launch_template_versions.py — Query Launch Template Version List

Purpose: Query the list of ECS launch template versions, including version_number, launch template ID, and creation time.
Usage: python scripts/ecs/list_launch_template_versions.py -h

---

### list_recycle_bin_servers.py — Query Recycle Bin Server List

Purpose: Query the list of ECS recycle bin servers, including ID, name, status, flavor_id.
Usage: python scripts/ecs/list_recycle_bin_servers.py -h

---

### list_scheduled_events.py — Query Scheduled Event List

Purpose: Query the list of ECS scheduled events, including ID, instance_id, type, state, publish_time.
Usage: python scripts/ecs/list_scheduled_events.py -h

---

### list_templates.py — Query Launch Template List

Purpose: Query the list of ECS launch templates, including ID, name, and creation time.
Usage: python scripts/ecs/list_templates.py -h

---

### show_server.py — Query Server Details

Purpose: Query ECS server details.
Usage: python scripts/ecs/show_server.py -h

---

### show_server_block_device.py — Query Single Block Device Details

Purpose: Query ECS server block device details.
Usage: python scripts/ecs/show_server_block_device.py -h

---

### show_server_group.py — Query Server Group Details

Purpose: Query ECS server group details.
Usage: python scripts/ecs/show_server_group.py -h

---

### show_server_limits.py — Query Tenant Quota

Purpose: Query ECS server quota.
Usage: python scripts/ecs/show_server_limits.py -h

---

### show_server_tags.py — Query Server Tags

Purpose: Query ECS server tag details, including key and value.
Usage: python scripts/ecs/show_server_tags.py -h

---

### show_server_password.py — Get Server Password

Purpose: Query ECS server password.
Usage: python scripts/ecs/show_server_password.py -h

---

### show_server_remote_console.py — Get VNC Remote Login Address

Purpose: Query ECS server remote console.
Usage: python scripts/ecs/show_server_remote_console.py -h

---

### show_server_attachable_nic_num.py — Query Attachable NIC Count

Purpose: Query the number of attachable NICs for an ECS server.
Usage: python scripts/ecs/show_server_attachable_nic_num.py -h

---

### show_appendable_volume_quota.py — Query Appendable Volume Quota

Purpose: Query the appendable volume quota for an ECS server.
Usage: python scripts/ecs/show_appendable_volume_quota.py -h

---

### show_flavor_capacity.py — Query Flavor Capacity

Purpose: Query ECS flavor capacity, including availability zone, region ID, and prefer.
Usage: python scripts/ecs/show_flavor_capacity.py -h

---

### show_metadata_options.py — Query Metadata Configuration

Purpose: Query ECS server metadata options.
Usage: python scripts/ecs/show_metadata_options.py -h

---

### show_recycle_bin.py — Query Recycle Bin Configuration

Purpose: Query ECS recycle bin configuration.
Usage: python scripts/ecs/show_recycle_bin.py -h

---

### show_reset_password_flag.py — Query Whether Password Reset is Supported

Purpose: Query the ECS server reset password flag.
Usage: python scripts/ecs/show_reset_password_flag.py -h

---

### show_serial_console_actions.py — Get Serial Console Login Address

Purpose: Query ECS server serial console.
Usage: python scripts/ecs/show_serial_console_actions.py -h

---

### show_job.py — Query Asynchronous Task Status

Purpose: Query ECS asynchronous task details.
Usage: python scripts/ecs/show_job.py -h

---

### nova_list_keypairs.py — Query SSH Keypair List

Purpose: Query the list of ECS SSH keypairs, including name, type, fingerprint.
Usage: python scripts/ecs/nova_list_keypairs.py -h

---

### nova_show_keypair.py — Query SSH Keypair Details

Purpose: Query ECS SSH keypair details, including name, type, fingerprint, public_key, created_at, user_id.
Usage: python scripts/ecs/nova_show_keypair.py -h

---

### nova_list_server_security_groups.py — Query Server Security Group List

Purpose: Query the list of ECS server security groups, including id, name, description.
Usage: python scripts/ecs/nova_list_server_security_groups.py -h

---

### nova_show_flavor_extra_specs.py — Query Flavor Extra Specs

Purpose: Query ECS flavor extra specs, including key and value.
Usage: python scripts/ecs/nova_show_flavor_extra_specs.py -h

---

### nova_show_server_interface.py — Query Server Specified NIC Details

Purpose: Query ECS server specified NIC details, including port_id, net_id, mac_addr, port_state, fixed_ips.
Usage: python scripts/ecs/nova_show_server_interface.py -h

---

## 分页上限与翻页语义（list_servers_details.py / list_cloud_servers.py）

**分页上限**

- 服务端单次 `limit` 上限为 `API_LIMIT = 1000`（`scripts/ecs/list_servers_details.py`、`scripts/ecs/list_cloud_servers.py` 中的常量）。
- 默认每页展示 `PAGE_SIZE = 50` 条。
- 常规查询（不使用 `--sort_by`）只发起 1 次请求，`limit = FETCH_SIZE = PAGE_SIZE + 1 = 51`，多查的 1 条仅用于判断「是否还有更多」，不会展示。

**翻页语义（重要，避免遗漏数据）**

- 不使用 `--sort_by` 时脚本**只查 1 页**（最多 51 条），不会自动翻页；若总数超过 50 条，输出末尾会给出 `next_marker`，必须用 `--marker=<next_marker>` 手动查询下一页，否则会漏掉后续数据。可用 `--tag` / `--not_tag` / `--name` / `--status` 等过滤条件缩小范围，减少翻页次数。
- 使用 `--sort_by`（配合 `--top`）时，脚本按 `API_LIMIT = 1000` 逐页全量拉取后再在客户端排序、截取，此时无需手动传 `--marker`；数据量很大时请留意耗时。

**导出的数据范围**

- `--export` 导出的是本次查询实际取得的结果：常规查询为当前页展示的、最多 `PAGE_SIZE = 50` 条；`--sort_by` 全量拉取时为本次拉取到的全部数据（`--top` 截取之后）。
- 需要导出全量数据时，请配合 `--sort_by`（自动全量拉取）或逐页 `--marker` 分别导出。
- 查询结果为空时不会生成导出文件。
