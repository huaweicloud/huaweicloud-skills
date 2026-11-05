# AI生成
#!/usr/bin/env python3
"""华为云 ECS 查询工具 - 主入口

支持三种查询操作：
  list-servers  - 查询云服务器列表
  show-server   - 查询单个云服务器详情
  server-status - 查询云服务器状态
"""

import argparse
import os
import sys
import json
from urllib.parse import quote
import requests
import yaml

# 将 scripts 目录加入路径以导入同目录模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from auth import create_auth
from formatter import output_result, extract_server_info, format_json


def load_config(config_path):
    """加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    # 默认配置路径
    if not config_path:
        home = os.path.expanduser("~")
        config_path = os.path.join(home, ".huawei-ecs", "config.yaml")

    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        print("请创建配置文件，参考 SKILL.md 中的配置说明。")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def create_auth_or_exit(config, endpoint=None):
    """创建认证实例，配置缺失时给出友好提示并退出

    Args:
        config: 包含认证信息的字典
        endpoint: 目标服务端点（如 evs.{region}.myhuaweicloud.com），默认使用 ECS 端点

    Returns:
        HuaweiCloudAuth 子类实例
    """
    try:
        return create_auth(config, endpoint=endpoint)
    except ValueError as e:
        print(f"错误: 配置错误: {e}")
        if "project_id" in str(e):
            print("提示: 多区域查询时，请在 config.yaml 的 regions 映射中配置目标区域对应的 project_id，")
            print("      或使用 --project-id <目标区域项目ID> 参数指定。")
        sys.exit(1)


def build_query_string(params):
    """构建 URL 查询字符串

    Args:
        params: 参数字典

    Returns:
        查询字符串（不含前导 ?），各 key/value 均已做 RFC3986 URL 编码
    """
    pairs = []
    for key, value in params.items():
        if value is not None:
            # 参数值与参数名均需 URL 编码，否则特殊字符（&、=、空格、中文等）
            # 会导致请求解析错误或与签名器编码不一致
            pairs.append(f"{quote(key, safe='~')}={quote(str(value), safe='~')}")
    return "&".join(pairs)


def make_request(auth, method, uri, params=None, fatal=True):
    """发送 API 请求

    Args:
        auth: 认证实例
        method: HTTP 方法
        uri: API 路径
        params: 查询参数字典
        fatal: 请求失败时是否终止程序；False 时返回 None 供增强查询降级

    Returns:
        响应 JSON 数据；fatal=False 且请求失败时返回 None
    """
    query_string = build_query_string(params) if params else ""
    full_uri = uri
    if query_string:
        full_uri = f"{uri}?{query_string}"

    url = f"https://{auth.endpoint}{full_uri}"

    # 获取认证头（Token 认证会在此发起 IAM 鉴权请求，需纳入异常处理，
    # 否则认证失败会抛出裸 traceback）
    try:
        headers = auth.get_headers(
            method=method,
            uri=uri,
            query_string=query_string,
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "N/A"
        if not fatal:
            return None
        print(f"错误: 认证失败 (HTTP {status_code})，请检查用户名/密码/域名配置是否正确。")
        sys.exit(1)
    except (ValueError, requests.exceptions.RequestException) as e:
        if not fatal:
            return None
        print(f"错误: 认证失败，请检查用户名/密码/域名配置是否正确。（{e}）")
        sys.exit(1)

    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        error_msg = f"API 请求失败 (HTTP {resp.status_code})"
        try:
            error_body = resp.json()
            error_msg += f": {json.dumps(error_body, ensure_ascii=False)}"
        except Exception:
            error_msg += f": {resp.text}"
        if not fatal:
            return None
        print(f"错误: {error_msg}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        if not fatal:
            return None
        print(f"错误: 无法连接到华为云 API 端点: {auth.endpoint}")
        print(f"请检查网络连接和区域配置是否正确。")
        sys.exit(1)
    except requests.exceptions.Timeout:
        if not fatal:
            return None
        print(f"错误: 请求超时，请检查网络连接。")
        sys.exit(1)


def fetch_extended_volume_details(auth, config):
    """查询 EVS 云硬盘详细信息，用于补全系统盘/数据盘大小与类型

    通过 EVS ListVolumes 一次性拉取项目下全部云硬盘，按磁盘ID建立索引。
    仅用于 --detail/--full 增强展示；失败时返回空字典（降级为仅展示磁盘ID/挂载点）。

    API: GET /v2/{project_id}/cloudvolumes/detail
    """
    endpoint = f"evs.{auth.region}.myhuaweicloud.com"
    evs_auth = create_auth_or_exit(config, endpoint=endpoint)
    uri = f"/v2/{auth.project_id}/cloudvolumes/detail"
    volume_map = {}
    offset = 0
    limit = 1000
    while True:
        data = make_request(
            evs_auth, "GET", uri, {"limit": limit, "offset": offset}, fatal=False
        )
        if not data or not isinstance(data, dict):
            break
        volumes = data.get("volumes", [])
        for vol in volumes:
            vol_id = vol.get("id")
            if vol_id:
                volume_map[vol_id] = vol
        count = data.get("count")
        if not volumes or (count is not None and offset + len(volumes) >= count):
            break
        if len(volumes) < limit:
            break
        offset += len(volumes)
        if offset > 5000:
            break
    return volume_map


def fetch_eip_bandwidth_map(auth, config):
    """查询弹性公网 IP 的带宽信息，用于补全 EIP 带宽展示

    通过 VPC/EIP ListPublicips/v3 拉取项目下全部弹性公网 IP，按 IP 地址建立索引。
    仅用于 --detail/--full 增强展示；失败时返回空字典（降级为仅展示 EIP 地址）。

    API: GET /v3/{project_id}/eip/publicips
    """
    endpoint = f"vpc.{auth.region}.myhuaweicloud.com"
    eip_auth = create_auth_or_exit(config, endpoint=endpoint)
    uri = f"/v3/{auth.project_id}/eip/publicips"
    eip_map = {}
    offset = 0
    limit = 100
    while True:
        data = make_request(
            eip_auth, "GET", uri, {"limit": limit, "offset": offset}, fatal=False
        )
        if not data or not isinstance(data, dict):
            break
        publicips = data.get("publicips", [])
        for eip in publicips:
            ip = eip.get("public_ip_address")
            if ip:
                bandwidth = eip.get("bandwidth") or {}
                eip_map[ip] = {
                    "bandwidth_size": bandwidth.get("size"),
                    "share_type": bandwidth.get("share_type"),
                }
        if not publicips or len(publicips) < limit:
            break
        offset += len(publicips)
        if offset > 2000:
            break
    return eip_map


def build_detail_context(auth, config, detail):
    """构建详情展示所需的增强上下文（EVS 磁盘信息 + EIP 带宽信息）

    Args:
        auth: 认证实例
        config: 配置字典
        detail: 是否启用 --detail/--full 增强

    Returns:
        增强上下文字典；未启用或获取失败时各字段为空字典
    """
    context = {"volumes": {}, "eips": {}}
    if not detail:
        return context
    try:
        context["volumes"] = fetch_extended_volume_details(auth, config)
    except SystemExit:
        pass
    try:
        context["eips"] = fetch_eip_bandwidth_map(auth, config)
    except SystemExit:
        pass
    return context


def list_servers(args, config):
    """查询云服务器列表

    API: GET /v1/{project_id}/cloudservers/detail
    """
    auth = create_auth_or_exit(config)
    uri = f"/v1/{auth.project_id}/cloudservers/detail"

    params = {
        "limit": args.limit,
        "offset": args.offset,
    }

    # 可选过滤参数
    if args.status:
        params["status"] = args.status
    if args.name:
        params["name"] = args.name
    if args.flavor:
        params["flavor"] = args.flavor

    data = make_request(auth, "GET", uri, params)
    detail_context = build_detail_context(auth, config, args.detail or args.full)
    output_format = args.output or config.get("output_format", "table")
    output_result(data, output_format, detail_context=detail_context, detail_level="full" if args.full else ("detail" if args.detail else ""))


def show_server(args, config):
    """查询单个云服务器详情

    API: GET /v1/{project_id}/cloudservers/{server_id}
    """
    if not args.server_id:
        print("错误: 请通过 --server-id 指定服务器ID")
        print("提示: 先用 list-servers --output json 查询实例列表，从输出的完整 ID 获取 server-id")
        print("示例: python scripts/ecs_query.py list-servers --config config.yaml --output json")
        sys.exit(1)

    auth = create_auth_or_exit(config)
    uri = f"/v1/{auth.project_id}/cloudservers/{args.server_id}"

    data = make_request(auth, "GET", uri)
    detail_context = build_detail_context(auth, config, args.detail or args.full)
    # API 返回的是服务器对象，包装为统一格式
    result = {"server": data.get("server", data)}
    output_format = args.output or config.get("output_format", "table")
    output_result(result, output_format, detail_context=detail_context, detail_level="full" if args.full else ("detail" if args.detail else ""))


def server_status(args, config):
    """查询云服务器状态

    API: GET /v1/{project_id}/cloudservers/{server_id}
    """
    if not args.server_id:
        print("错误: 请通过 --server-id 指定服务器ID")
        print("提示: 先用 list-servers --output json 查询实例列表，从输出的完整 ID 获取 server-id")
        print("示例: python scripts/ecs_query.py list-servers --config config.yaml --output json")
        sys.exit(1)

    auth = create_auth_or_exit(config)
    uri = f"/v1/{auth.project_id}/cloudservers/{args.server_id}"

    data = make_request(auth, "GET", uri)
    server = data.get("server", data)

    # 提取状态信息
    status_data = {
        "id": server.get("id", "N/A"),
        "name": server.get("name", "N/A"),
        "status": server.get("status", "N/A"),
        "OS-EXT-AZ:availability_zone": server.get("OS-EXT-AZ:availability_zone", "N/A"),
        "updated": server.get("updated", "N/A"),
        "OS-EXT-STS:vm_state": server.get("OS-EXT-STS:vm_state", "N/A"),
        "OS-EXT-STS:task_state": server.get("OS-EXT-STS:task_state", None),
        "OS-EXT-STS:power_state": server.get("OS-EXT-STS:power_state", "N/A"),
    }

    # 统一走 output_result 复用 formatter.format_status 格式化，
    # 消除脚本内重复实现
    output_format = args.output or config.get("output_format", "table")
    output_result(status_data, output_format)


def main():
    """主函数 - 解析命令行参数并执行对应操作"""
    parser = argparse.ArgumentParser(
        description="华为云 ECS 查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询云服务器列表（表格格式）
  python ecs_query.py list-servers --config config.yaml

  # 查询云服务器列表（JSON 格式，指定区域）
  python ecs_query.py list-servers --region cn-east-3 --output json

  # 多区域查询（需在 config.yaml regions 映射中配置目标区域 project_id，
  # 或使用 --project-id 指定目标区域的项目ID）
  python ecs_query.py list-servers --region cn-south-1 --project-id <cn-south-1项目ID>

  # 按状态过滤
  python ecs_query.py list-servers --status ACTIVE

  # 查询列表（展示完整运维字段：磁盘/SG/VPC/镜像/密钥/标签/EIP带宽/计费）
  python ecs_query.py list-servers --detail

  # 查询服务器详情
  python ecs_query.py show-server --server-id abc123-def456

  # 查询服务器详情（展示全部增强字段）
  python ecs_query.py show-server --server-id abc123-def456 --full

  # 查询服务器状态
  python ecs_query.py server-status --server-id abc123-def456
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="查询命令")

    # list-servers 子命令
    list_parser = subparsers.add_parser("list-servers", help="查询云服务器列表")
    list_parser.add_argument("--limit", type=int, default=25, help="返回数量限制（默认25）")
    list_parser.add_argument("--offset", type=int, default=1, help="页码偏移（默认1）")
    list_parser.add_argument("--status", type=str, help="按状态过滤（ACTIVE, SHUTOFF, BUILD, ERROR等）")
    list_parser.add_argument("--name", type=str, help="按名称过滤")
    list_parser.add_argument("--flavor", type=str, help="按规格ID过滤")
    list_parser.add_argument("--detail", action="store_true", help="展示完整运维字段（含系统盘/数据盘大小类型、安全组、VPC/子网、镜像名称、密钥对、标签、EIP带宽、计费模式）")
    list_parser.add_argument("--full", action="store_true", help="同 --detail，展示全部增强字段")

    # show-server 子命令
    show_parser = subparsers.add_parser("show-server", help="查询单个云服务器详情")
    show_parser.add_argument("--server-id", type=str, help="云服务器ID（先用 list-servers 获取）")
    show_parser.add_argument("--detail", action="store_true", help="展示完整运维字段（含系统盘/数据盘大小类型、安全组、VPC/子网、镜像名称、密钥对、标签、EIP带宽、计费模式）")
    show_parser.add_argument("--full", action="store_true", help="同 --detail，展示全部增强字段")

    # server-status 子命令
    status_parser = subparsers.add_parser("server-status", help="查询云服务器状态")
    status_parser.add_argument("--server-id", type=str, help="云服务器ID（先用 list-servers 获取）")

    # 公共参数
    for sub_parser in [list_parser, show_parser, status_parser]:
        sub_parser.add_argument("--config", type=str, default=None, help="配置文件路径")
        sub_parser.add_argument("--region", type=str, default=None, help="区域（如 cn-north-4）")
        sub_parser.add_argument("--project-id", type=str, default=None, help="目标区域对应的项目ID（多区域查询时与 --region 配套使用）")
        sub_parser.add_argument("--output", type=str, choices=["table", "json"], default=None, help="输出格式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置
    if args.region:
        config["region"] = args.region

    # 多区域查询支持：--region 切换时同步匹配 regions 映射中的 project_id。
    # 修复：仅覆盖 config["region"] 而不联动 project_id，会导致跨区域查询必现
    # Common.0018（tenantId in token is not the same with in URL）。
    if args.project_id:
        config["project_id"] = args.project_id
    else:
        region_project_map = config.get("regions") or {}
        mapped_project_id = region_project_map.get(config["region"])
        if mapped_project_id:
            config["project_id"] = mapped_project_id

    # 执行对应命令
    if args.command == "list-servers":
        list_servers(args, config)
    elif args.command == "show-server":
        show_server(args, config)
    elif args.command == "server-status":
        server_status(args, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
