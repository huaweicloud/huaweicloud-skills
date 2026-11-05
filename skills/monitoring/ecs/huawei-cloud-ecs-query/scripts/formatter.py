#!/usr/bin/env python3
"""输出格式化模块 - 支持表格和 JSON 两种输出格式"""

import json
import sys

# 状态映射
STATUS_MAP = {
    "ACTIVE": "运行中",
    "SHUTOFF": "已关机",
    "BUILD": "创建中",
    "ERROR": "故障",
    "REBOOT": "重启中",
    "HARD_REBOOT": "强制重启中",
    "MIGRATING": "迁移中",
    "RESIZE": "规格变更中",
    "VERIFY_RESIZE": "规格变更验证中",
    "PAUSED": "暂停",
    "SUSPENDED": "挂起",
    "DELETED": "已删除",
}


def get_status_text(status):
    """获取状态的中文说明"""
    return STATUS_MAP.get(status, status)


# 计费模式映射（metadata.charging_mode）
CHARGING_MODE_MAP = {
    "0": "按需计费",
    "1": "包年/包月",
    "2": "竞价计费",
}


def get_charging_mode_text(mode):
    """获取计费模式的中文说明"""
    if not mode:
        return "N/A"
    return CHARGING_MODE_MAP.get(str(mode), str(mode))


def extract_server_info(server, detail_context=None):
    """从服务器数据中提取关键信息

    Args:
        server: API 返回的单个服务器对象
        detail_context: 增强上下文字典，含 volumes（磁盘ID→云硬盘信息）与 eips（EIP地址→带宽信息）

    Returns:
        包含关键信息的字典
    """
    detail_context = detail_context or {}
    volume_map = detail_context.get("volumes", {})
    eip_map = detail_context.get("eips", {})

    # 提取 IP 地址
    # NOTE: iterates over already-fetched server.addresses data (single API call
    # in list_servers/show_server); local iteration only, not N+1
    private_ips = []
    public_ips = []
    addresses = server.get("addresses", {})
    for network_name, ip_list in addresses.items():
        for ip_info in ip_list:
            ip_type = ip_info.get("OS-EXT-IPS:type", "fixed")
            if ip_type == "fixed":
                private_ips.append(ip_info.get("addr", ""))
            elif ip_type == "floating":
                public_ips.append(ip_info.get("addr", ""))

    # 提取规格信息
    flavor = server.get("flavor", {})
    flavor_name = flavor.get("name", "N/A")
    vcpus = flavor.get("vcpus", "N/A")
    ram = flavor.get("ram", "N/A")

    # 提取可用区
    az = server.get("OS-EXT-AZ:availability_zone", "N/A")

    # 提取镜像信息
    image = server.get("image", {})
    image_id = image.get("id", "N/A") if image else "N/A"

    # 提取创建时间
    created = server.get("created", "N/A")
    updated = server.get("updated", "N/A")

    # 提取元数据
    metadata = server.get("metadata", {})
    os_type = metadata.get("os_type", "N/A")
    charging_mode = metadata.get("charging_mode", "N/A")
    image_name = metadata.get("image_name")
    vpc_id = metadata.get("vpc_id")

    # 提取 VPC/子网：优先取 network_interfaces，降级用 metadata.vpc_id
    subnet_id = None
    network_interfaces = server.get("network_interfaces") or []
    if network_interfaces and isinstance(network_interfaces, list):
        subnet_id = network_interfaces[0].get("subnet_id")
    else:
        subnet_id = metadata.get("subnet_id")

    # 提取安全组
    security_groups = server.get("security_groups", [])
    security_group_names = [
        sg.get("name") for sg in security_groups if isinstance(sg, dict) and sg.get("name")
    ]

    # 提取密钥对
    key_name = server.get("key_name")

    # 提取标签
    tags = server.get("tags", [])

    # 提取挂载的云硬盘（API 扩展字段 os-extended-volumes:volumes_attached）
    volumes_attached = server.get("os-extended-volumes:volumes_attached", [])
    volumes = []
    system_disk = None
    data_disks = []
    for vol in volumes_attached:
        vol_id = vol.get("id", "")
        if not vol_id:
            continue
        device = vol.get("device", "")
        boot_index = vol.get("bootIndex")
        volume_info = volume_map.get(vol_id, {})
        entry = {
            "id": vol_id,
            "device": device,
            "size": volume_info.get("size") if volume_info else None,
            "volume_type": volume_info.get("volume_type") if volume_info else None,
        }
        volumes.append(entry)
        # bootIndex 为 "0" 表示系统盘，"-1" 表示数据盘
        if boot_index == "0":
            system_disk = entry
        else:
            data_disks.append(entry)
    # 若 API 未返回 bootIndex，则第一个挂载盘视为系统盘（降级处理）
    if system_disk is None and volumes:
        system_disk = volumes[0]
        if system_disk in data_disks:
            data_disks.remove(system_disk)

    # EIP 带宽
    eip_bandwidths = []
    for ip in public_ips:
        eip_info = eip_map.get(ip, {})
        if eip_info:
            bw = eip_info.get("bandwidth_size")
            eip_bandwidths.append({
                "ip": ip,
                "bandwidth_size": bw,
                "share_type": eip_info.get("share_type"),
            })

    return {
        "id": server.get("id", "N/A"),
        "name": server.get("name", "N/A"),
        "status": server.get("status", "N/A"),
        "status_text": get_status_text(server.get("status", "")),
        "flavor": flavor_name,
        "vcpus": vcpus,
        "ram_mb": ram,
        "private_ips": private_ips,
        "public_ips": public_ips,
        "eip_bandwidths": eip_bandwidths,
        "availability_zone": az,
        "image_id": image_id,
        "image_name": image_name,
        "os_type": os_type,
        "charging_mode": get_charging_mode_text(charging_mode),
        "charging_mode_raw": charging_mode,
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "security_group_names": security_group_names,
        "key_name": key_name,
        "created": created,
        "updated": updated,
        "tenant_id": server.get("tenant_id", "N/A"),
        "user_id": server.get("user_id", "N/A"),
        "enterprise_project_id": server.get("enterprise_project_id", "N/A"),
        "locked": server.get("locked", False),
        "description": server.get("description", ""),
        "tags": tags,
        "system_disk": system_disk,
        "data_disks": data_disks,
        "volumes": volumes,
        "vm_state": server.get("OS-EXT-STS:vm_state", "N/A"),
        "task_state": server.get("OS-EXT-STS:task_state"),
        "power_state": server.get("OS-EXT-STS:power_state", "N/A"),
    }


def format_json(data):
    """JSON 格式输出

    Args:
        data: 要输出的数据

    Returns:
        JSON 字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_disk(disk):
    """格式化磁盘展示：`80G (SSD) @/dev/vda`"""
    if not disk:
        return "N/A"
    parts = []
    size = disk.get("size")
    volume_type = disk.get("volume_type")
    if size:
        parts.append(f"{size}G")
    if volume_type:
        parts.append(f"({volume_type})")
    if disk.get("device"):
        parts.append(f"@{disk['device']}")
    if not parts:
        return disk.get("id", "N/A")[:8] if disk.get("id") else "N/A"
    return " ".join(parts)


def _format_eip_bandwidth(eip):
    """格式化 EIP 带宽展示：`1.2.3.4 (10Mbps)`"""
    if not eip:
        return "N/A"
    bw = eip.get("bandwidth_size")
    if bw is not None:
        return f"{eip.get('ip', '')} ({bw}Mbps)"
    return eip.get("ip", "")


def format_table(servers_info, count=None, detail_level=""):
    """表格格式输出

    Args:
        servers_info: 服务器信息列表
        count: 总数（可选）
        detail_level: 详细程度，空（默认表格）/ "detail"（增强字段）/ "full"（相同增强字段）

    Returns:
        表格字符串
    """
    if not servers_info:
        return "没有找到符合条件的云服务器实例。"

    # 定义列
    headers = [
        "ID",
        "Name",
        "Status",
        "Flavor",
        "vCPU",
        "RAM(MB)",
        "Private IP",
        "Public IP",
        "Created",
        "AZ",
    ]

    detail = bool(detail_level)
    if detail:
        headers += [
            "System Disk",
            "Data Disks",
            "Security Group",
            "VPC/Subnet",
            "Image",
            "KeyPair",
            "Tags",
            "EIP(BW)",
            "Billing",
        ]

    # 构建行数据
    rows = []
    for info in servers_info:
        row = [
            info["id"][:8] + "..." if len(info["id"]) > 11 else info["id"],
            info["name"],
            f"{info['status']} ({info['status_text']})",
            info["flavor"],
            str(info["vcpus"]),
            str(info["ram_mb"]),
            ", ".join(info["private_ips"]) or "N/A",
            ", ".join(info["public_ips"]) or "N/A",
            info["created"][:19] if info["created"] != "N/A" else "N/A",
            info["availability_zone"],
        ]

        if detail:
            data_disks = info.get("data_disks", [])
            data_disk_text = (
                "; ".join(_format_disk(d) for d in data_disks) if data_disks else "无"
            )
            vpc_subnet = ""
            if info.get("vpc_id") and info.get("subnet_id"):
                vpc_subnet = f"{info['vpc_id'][:8]}.../{info['subnet_id'][:8]}..."
            elif info.get("vpc_id"):
                vpc_subnet = info["vpc_id"][:8] + "..."
            eip_bw_text = (
                "; ".join(_format_eip_bandwidth(e) for e in info.get("eip_bandwidths", []))
                if info.get("eip_bandwidths")
                else (", ".join(info["public_ips"]) or "无")
            )
            tags = info.get("tags", [])
            secure_group_text = ", ".join(info.get("security_group_names", [])) if info.get("security_group_names") else "无"
            row += [
                _format_disk(info.get("system_disk")),
                data_disk_text,
                secure_group_text,
                vpc_subnet or "N/A",
                info.get("image_name") or info.get("image_id", "N/A"),
                info.get("key_name") or "N/A",
                ", ".join(tags) if tags else "无",
                eip_bw_text,
                info.get("charging_mode", "N/A"),
            ]

        rows.append(row)

    # 计算列宽
    col_widths = []
    for i in range(len(headers)):
        max_width = len(headers[i])
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)

    # 构建表格
    lines = []

    # 标题行
    if count is not None:
        lines.append(f"共找到 {count} 台云服务器（当前显示 {len(servers_info)} 台）")
        lines.append("")
    lines.append("提示: 表格中 ID 列已截断（仅显示前 8 位），复制完整 ID 请使用 --output json")
    if detail:
        lines.append("提示: 增强列中的系统盘/数据盘大小与类型、EIP带宽来自 EVS/EIP 接口（未授权时显示挂载盘/地址）")
    lines.append("")

    # 表头
    header_line = ""
    for i, header in enumerate(headers):
        header_line += header.ljust(col_widths[i])
    lines.append(header_line)

    # 分隔线
    separator = ""
    for width in col_widths:
        separator += "-" * width
    lines.append(separator)

    # 数据行
    for row in rows:
        row_line = ""
        for i, cell in enumerate(row):
            row_line += str(cell).ljust(col_widths[i])
        lines.append(row_line)

    return "\n".join(lines)


def format_server_detail(server_info, detail_level=""):
    """格式化单个服务器详情

    Args:
        server_info: 服务器信息字典
        detail_level: 详细程度，空（原详情）/ "detail"（增强字段）/"full"（全部增强字段）

    Returns:
        格式化的详情字符串
    """
    detail = bool(detail_level)
    lines = []
    lines.append("=" * 60)
    lines.append(f"  云服务器详情: {server_info['name']}")
    lines.append("=" * 60)
    lines.append("")

    detail_items = [
        ("服务器ID", server_info["id"]),
        ("名称", server_info["name"]),
        ("状态", f"{server_info['status']} ({server_info['status_text']})"),
        ("规格", server_info["flavor"]),
        ("vCPU", str(server_info["vcpus"])),
        ("内存(MB)", str(server_info["ram_mb"])),
        ("私有IP", ", ".join(server_info["private_ips"]) or "N/A"),
        ("公网IP", ", ".join(server_info["public_ips"]) or "N/A"),
        ("可用区", server_info["availability_zone"]),
        ("镜像ID", server_info["image_id"]),
        ("镜像名称", server_info.get("image_name") or "N/A"),
        ("操作系统", server_info["os_type"]),
        ("安全组", ", ".join(server_info.get("security_group_names", [])) or "N/A"),
        ("VPC ID", server_info.get("vpc_id") or "N/A"),
        ("子网 ID", server_info.get("subnet_id") or "N/A"),
        ("密钥对", server_info.get("key_name") or "N/A"),
        ("计费模式", server_info["charging_mode"]),
        ("创建时间", server_info["created"]),
        ("更新时间", server_info["updated"]),
        ("租户ID", server_info["tenant_id"]),
        ("用户ID", server_info["user_id"]),
        ("企业项目ID", server_info["enterprise_project_id"]),
        ("是否锁定", str(server_info["locked"])),
        ("挂载云硬盘", "; ".join(
            f"{vol['device']} ({vol['id']})" for vol in server_info.get("volumes", []) if vol.get("device") and vol.get("id")
        ) or "N/A"),
        ("描述", server_info["description"] or "N/A"),
    ]

    if detail:
        # 增强字段：系统盘/数据盘大小类型、EIP带宽（需额外 EVS/EIP 接口调用）
        detail_enhanced = [
            ("系统盘", _format_disk(server_info.get("system_disk"))),
            ("数据盘", "; ".join(
                _format_disk(d) for d in server_info.get("data_disks", [])
            ) or "无"),
        ]
        # EIP 带宽单独处理（均含在列表增强中；若无浮动 IP 则降级展示公网IP）
        eip_bw = [
            _format_eip_bandwidth(e) for e in server_info.get("eip_bandwidths", [])
        ] if server_info.get("eip_bandwidths") else []
        if eip_bw:
            detail_enhanced.append(("EIP带宽", "; ".join(eip_bw)))
        detail_items = detail_enhanced + detail_items

    # NOTE: iterates over already-built local detail_items list; no API call in loop
    for label, value in detail_items:
        lines.append(f"  {label:.<20s}: {value}")

    # 标签单独列出（可能为空）
    if server_info.get("tags"):
        lines.append(f"  {'标签':.<20s}: {', '.join(server_info['tags'])}")
    elif detail:
        lines.append(f"  {'标签':.<20s}: 无")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_status(server_info):
    """格式化服务器状态

    Args:
        server_info: 服务器信息字典

    Returns:
        格式化的状态字符串
    """
    lines = []
    lines.append("=" * 40)
    lines.append(f"  服务器状态查询结果")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"  服务器名称: {server_info['name']}")
    lines.append(f"  服务器ID: {server_info['id']}")
    lines.append(f"  状态: {server_info['status']} ({server_info['status_text']})")
    lines.append(f"  VM状态: {server_info['vm_state']}")
    if server_info.get("task_state"):
        lines.append(f"  任务状态: {server_info['task_state']}")
    lines.append(f"  电源状态: {server_info['power_state']}")
    lines.append(f"  可用区: {server_info['availability_zone']}")
    lines.append(f"  更新时间: {server_info['updated']}")
    lines.append("")
    lines.append("=" * 40)

    return "\n".join(lines)


def output_result(data, output_format="table", detail_context=None, detail_level=""):
    """根据指定格式输出结果

    Args:
        data: 要输出的数据
        output_format: 输出格式 (table 或 json)
        detail_context: 增强上下文字典（磁盘/带宽信息）
        detail_level: 详细程度（""/"detail"/"full"），用于表格与详情输出
    """
    detail_context = detail_context or {}
    if output_format == "json":
        if isinstance(data, dict) and "servers" in data:
            print(format_json(data))
        elif isinstance(data, list):
            print(format_json(data))
        else:
            print(format_json(data))
    else:
        if isinstance(data, dict) and "servers" in data:
            servers_info = [extract_server_info(s, detail_context) for s in data["servers"]]
            print(format_table(servers_info, data.get("count"), detail_level=detail_level))
        elif isinstance(data, dict) and "server" in data:
            server_info = extract_server_info(data["server"], detail_context)
            print(format_server_detail(server_info, detail_level))
        elif isinstance(data, dict) and "status" in data:
            server_info = extract_server_info(data)
            print(format_status(server_info))
        else:
            print(format_json(data))
