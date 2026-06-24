# ECS Python Script Usage Guide

---

## List Query Scripts

### list_servers_details.py — Query ECS Instance List

Purpose: Query the list of ECS instances, including ID, name, status, flavor_id, vCPU, memory(GiB).
Usage: python scripts/ecs/list_servers_details.py -h

---

### list_servers_details_by_id.py — Query ECS Details by Instance ID

Purpose: Query ECS instance details, including name, status, flavor_id, vCPU, memory(GiB).
Usage: python scripts/ecs/list_servers_details_by_id.py -h

---

### list_cloud_servers.py — Query Cloud Server List (v1.1)

Purpose: Query the list of ECS cloud servers, including name, status, flavor_id, vCPU, ram(GiB), image ID.
Usage: python scripts/ecs/list_cloud_servers.py -h

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
