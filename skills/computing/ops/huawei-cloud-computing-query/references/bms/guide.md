# BMS (Bare Metal Server) Query Guide

## List Query

### list_bare_metal_servers.py — Query Bare Metal Server List (OpenStack Native, with Total Count)

Purpose: Query the list of bare metal servers, returning key information such as server ID, name, status, flavor, vCPU, memory, disk, availability zone, and creation time, including total count.
Usage: python scripts/bms/list_bare_metal_servers.py -h

### list_bare_metal_servers_detail.py — Query Bare Metal Server Detail List (OpenStack Native, without Total Count)

Purpose: Query the detail list of bare metal servers, returning key information such as server ID, name, status, flavor, vCPU, memory, disk, availability zone, and creation time, without total count.
Usage: python scripts/bms/list_bare_metal_servers_detail.py -h

### list_bare_metal_server_details.py — Query Bare Metal Server Details (by ID)

Purpose: Query detailed information of a single bare metal server by server ID, including flavor details (GPU/ASIC accelerators), image, metadata (billing mode, OS type, etc.), attached disks, tags, etc.
Usage: python scripts/bms/list_bare_metal_server_details.py -h

### list_baremetal_flavor_detail_extends.py — Query Bare Metal Server Flavor Detail List

Purpose: Query the list of bare metal server flavor details, returning flavor ID, name, vCPU, memory, disk, resource type, CPU architecture, disk details, etc.
Usage: python scripts/bms/list_baremetal_flavor_detail_extends.py -h

---

## Detail Query

### show_available_resource.py — Query Availability Zone Resource Information

Purpose: Query the resource availability of bare metal servers for a specified availability zone and flavor, returning availability zone, flavor ID, available count, and status.
Usage: python scripts/bms/show_available_resource.py -h

### show_baremetal_server_interface_attachments.py — Query Bare Metal Server NIC Information

Purpose: Query the NIC information of a specified bare metal server, returning port ID, network ID, MAC address, port state, driver mode, PCI address, IP address, etc.
Usage: python scripts/bms/show_baremetal_server_interface_attachments.py -h

### show_baremetal_server_tags.py — Query Bare Metal Server Tags

Purpose: Query the tag list of a specified bare metal server, returning tag key and value.
Usage: python scripts/bms/show_baremetal_server_tags.py -h

### show_baremetal_server_volume_info.py — Query Bare Metal Server Attached Disk Information

Purpose: Query the attached disk information of a specified bare metal server, returning disk ID, server ID, volume ID, and device name.
Usage: python scripts/bms/show_baremetal_server_volume_info.py -h

### show_job_infos.py — Query Asynchronous Task Status

Purpose: Query the status information of an asynchronous task, returning task ID, status, type, start time, end time, error code, failure reason, etc., including subtask information.
Usage: python scripts/bms/show_job_infos.py -h

### show_metadata_options.py — Query Bare Metal Server Metadata Configuration

Purpose: Query the metadata configuration of a specified bare metal server, returning http_endpoint and http_tokens configuration.
Usage: python scripts/bms/show_metadata_options.py -h

### show_reset_pwd.py — Query Whether Bare Metal Server Supports Password Reset

Purpose: Query whether a specified bare metal server supports password reset, returning the resetpwd_flag.
Usage: python scripts/bms/show_reset_pwd.py -h

### show_server_remote_console.py — Get Bare Metal Server VNC Remote Login Address

Purpose: Get the VNC remote login address of a specified bare metal server, returning protocol, type, and URL.
Usage: python scripts/bms/show_server_remote_console.py -h

### show_specified_version.py — Query BMS API Specified Version Information

Purpose: Query the specified version information of BMS API, returning version ID, status, minimum version, update time, etc.
Usage: python scripts/bms/show_specified_version.py -h

### show_tenant_quota.py — Query Bare Metal Server Tenant Quota

Purpose: Query the bare metal server quota information of the current tenant, returning max instances, used instances, max cores, used cores, max memory, used memory, and other quota data.
Usage: python scripts/bms/show_tenant_quota.py -h

### show_windows_baremetal_server_pwd.py — Query Windows Bare Metal Server Initial Password

Purpose: Query the initial password of a specified Windows bare metal server, returning the encrypted password.
Usage: python scripts/bms/show_windows_baremetal_server_pwd.py -h
