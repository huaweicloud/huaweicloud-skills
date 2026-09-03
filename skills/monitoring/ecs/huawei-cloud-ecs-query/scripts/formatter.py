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


def extract_server_info(server):
    """从服务器数据中提取关键信息

    Args:
        server: API 返回的单个服务器对象

    Returns:
        包含关键信息的字典
    """
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
        "availability_zone": az,
        "image_id": image_id,
        "os_type": os_type,
        "charging_mode": charging_mode,
        "created": created,
        "updated": updated,
        "tenant_id": server.get("tenant_id", "N/A"),
        "user_id": server.get("user_id", "N/A"),
        "enterprise_project_id": server.get("enterprise_project_id", "N/A"),
        "locked": server.get("locked", False),
        "description": server.get("description", ""),
        "tags": server.get("tags", []),
    }


def format_json(data):
    """JSON 格式输出

    Args:
        data: 要输出的数据

    Returns:
        JSON 字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_table(servers_info, count=None):
    """表格格式输出

    Args:
        servers_info: 服务器信息列表
        count: 总数（可选）

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

    # 构建行数据
    rows = []
    for info in servers_info:
        rows.append([
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
        ])

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


def format_server_detail(server_info):
    """格式化单个服务器详情

    Args:
        server_info: 服务器信息字典

    Returns:
        格式化的详情字符串
    """
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
        ("操作系统", server_info["os_type"]),
        ("计费模式", server_info["charging_mode"]),
        ("创建时间", server_info["created"]),
        ("更新时间", server_info["updated"]),
        ("租户ID", server_info["tenant_id"]),
        ("用户ID", server_info["user_id"]),
        ("企业项目ID", server_info["enterprise_project_id"]),
        ("是否锁定", str(server_info["locked"])),
        ("描述", server_info["description"] or "N/A"),
    ]

    # NOTE: iterates over already-built local detail_items list; no API call in loop
    for label, value in detail_items:
        lines.append(f"  {label:.<20s}: {value}")

    if server_info.get("tags"):
        lines.append(f"  {'标签':.<20s}: {', '.join(server_info['tags'])}")

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
    lines.append(f"  可用区: {server_info['availability_zone']}")
    lines.append(f"  更新时间: {server_info['updated']}")
    lines.append("")
    lines.append("=" * 40)

    return "\n".join(lines)


def output_result(data, output_format="table"):
    """根据指定格式输出结果

    Args:
        data: 要输出的数据
        output_format: 输出格式 (table 或 json)
    """
    if output_format == "json":
        if isinstance(data, dict) and "servers" in data:
            print(format_json(data))
        elif isinstance(data, list):
            print(format_json(data))
        else:
            print(format_json(data))
    else:
        if isinstance(data, dict) and "servers" in data:
            servers_info = [extract_server_info(s) for s in data["servers"]]
            print(format_table(servers_info, data.get("count")))
        elif isinstance(data, dict) and "server" in data:
            server_info = extract_server_info(data["server"])
            print(format_server_detail(server_info))
        elif isinstance(data, dict) and "status" in data:
            server_info = extract_server_info(data)
            print(format_status(server_info))
        else:
            print(format_json(data))
