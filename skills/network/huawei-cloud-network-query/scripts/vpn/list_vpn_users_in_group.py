import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListVpnUsersInGroupRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 用户组内用户列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_server_id", type=str, required=True, help="VPN 服务端 ID，可通过 list_vpn_servers_by_project.py 获取")
parser.add_argument("--group_id", type=str, required=True, help="用户组 ID，可通过 list_vpn_user_groups.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 VPN 用户组内用户列表
    :param items: 用户列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 VPN 用户组内用户")
        return

    output = f"id\tname\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        description = getattr(item, 'description', '')
        output += f"{id}\t{name}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    # 只查1次
    request = ListVpnUsersInGroupRequest()
    request.vpn_server_id = args.vpn_server_id
    request.group_id = args.group_id
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker

    response = client.list_vpn_users_in_group(request)
    items = response.users

    if not items:
        print(f"没有找到 VPN 用户组内用户 (区域: {Region}, VPN 服务端 ID: {args.vpn_server_id}, 用户组 ID: {args.group_id})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        total_count = getattr(response, 'total_count', None)
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            has_more = len(items) > PAGE_SIZE
        if has_more and len(items) > PAGE_SIZE:
            next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    total_count = getattr(response, 'total_count', None)
    render(display_items, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_vpn_users_in_group 查询失败: {e}")
    exit(1)
