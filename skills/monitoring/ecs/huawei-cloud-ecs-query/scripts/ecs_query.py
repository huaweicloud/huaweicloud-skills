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


def build_query_string(params):
    """构建 URL 查询字符串

    Args:
        params: 参数字典

    Returns:
        查询字符串（不含前导 ?）
    """
    pairs = []
    for key, value in params.items():
        if value is not None:
            pairs.append(f"{key}={value}")
    return "&".join(pairs)


def make_request(auth, method, uri, params=None):
    """发送 API 请求

    Args:
        auth: 认证实例
        method: HTTP 方法
        uri: API 路径
        params: 查询参数字典

    Returns:
        响应 JSON 数据
    """
    query_string = build_query_string(params) if params else ""
    full_uri = uri
    if query_string:
        full_uri = f"{uri}?{query_string}"

    url = f"https://{auth.endpoint}{full_uri}"

    # 获取认证头
    headers = auth.get_headers(
        method=method,
        uri=uri,
        query_string=query_string,
    )

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
        print(f"错误: {error_msg}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"错误: 无法连接到华为云 API 端点: {auth.endpoint}")
        print(f"请检查网络连接和区域配置是否正确。")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"错误: 请求超时，请检查网络连接。")
        sys.exit(1)


def list_servers(args, config):
    """查询云服务器列表

    API: GET /v1/{project_id}/cloudservers/detail
    """
    auth = create_auth(config)
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
    output_format = args.output or config.get("output_format", "table")
    output_result(data, output_format)


def show_server(args, config):
    """查询单个云服务器详情

    API: GET /v1/{project_id}/cloudservers/{server_id}
    """
    if not args.server_id:
        print("错误: 请通过 --server-id 指定服务器ID")
        print("提示: 先用 list-servers 查询实例列表，从输出的 ID 列获取 server-id")
        print("示例: python scripts/ecs_query.py list-servers --config config.yaml")
        sys.exit(1)

    auth = create_auth(config)
    uri = f"/v1/{auth.project_id}/cloudservers/{args.server_id}"

    data = make_request(auth, "GET", uri)
    # API 返回的是服务器对象，包装为统一格式
    result = {"server": data.get("server", data)}
    output_format = args.output or config.get("output_format", "table")
    output_result(result, output_format)


def server_status(args, config):
    """查询云服务器状态

    API: GET /v1/{project_id}/cloudservers/{server_id}
    """
    if not args.server_id:
        print("错误: 请通过 --server-id 指定服务器ID")
        print("提示: 先用 list-servers 查询实例列表，从输出的 ID 列获取 server-id")
        print("示例: python scripts/ecs_query.py list-servers --config config.yaml")
        sys.exit(1)

    auth = create_auth(config)
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

    output_format = args.output or config.get("output_format", "table")
    if output_format == "json":
        print(format_json(status_data))
    else:
        from formatter import get_status_text
        print("=" * 40)
        print("  服务器状态查询结果")
        print("=" * 40)
        print("")
        print(f"  服务器名称: {status_data['name']}")
        print(f"  服务器ID: {status_data['id']}")
        print(f"  状态: {status_data['status']} ({get_status_text(status_data['status'])})")
        print(f"  VM状态: {status_data['OS-EXT-STS:vm_state']}")
        if status_data.get("OS-EXT-STS:task_state"):
            print(f"  任务状态: {status_data['OS-EXT-STS:task_state']}")
        print(f"  电源状态: {status_data['OS-EXT-STS:power_state']}")
        print(f"  可用区: {status_data['OS-EXT-AZ:availability_zone']}")
        print(f"  更新时间: {status_data['updated']}")
        print("")
        print("=" * 40)


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

  # 按状态过滤
  python ecs_query.py list-servers --status ACTIVE

  # 查询服务器详情
  python ecs_query.py show-server --server-id abc123-def456

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

    # show-server 子命令
    show_parser = subparsers.add_parser("show-server", help="查询单个云服务器详情")
    show_parser.add_argument("--server-id", type=str, help="云服务器ID（先用 list-servers 获取）")

    # server-status 子命令
    status_parser = subparsers.add_parser("server-status", help="查询云服务器状态")
    status_parser.add_argument("--server-id", type=str, help="云服务器ID（先用 list-servers 获取）")

    # 公共参数
    for sub_parser in [list_parser, show_parser, status_parser]:
        sub_parser.add_argument("--config", type=str, default=None, help="配置文件路径")
        sub_parser.add_argument("--region", type=str, default=None, help="区域（如 cn-north-4）")
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
