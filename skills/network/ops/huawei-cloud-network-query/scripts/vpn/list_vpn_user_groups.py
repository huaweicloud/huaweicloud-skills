import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListVpnUserGroupsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限（SDK 未说明上限，保守设定）

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 用户组列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_server_id", type=str, required=True, help="VPN 服务端 ID，可通过 list_vpn_servers_by_project.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: user_number；方向可选: asc(升序), desc(降序)。例如 user_number:desc 表示按用户数量降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by user_number:desc --top 5 查找用户数量最多的 5 个用户组")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by user_number:desc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('user_number',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: user_number；方向可选: asc, desc。例如 user_number:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 VPN 用户组列表
    :param items: 用户组列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 VPN 用户组")
        return

    output = f"id\tname\tdescription\ttype\tuser_number\tcreated_at\tupdated_at\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        description = getattr(item, 'description', '')
        type_ = getattr(item, 'type', '')
        user_number = getattr(item, 'user_number', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        output += f"{id}\t{name}\t{description}\t{type_}\t{user_number}\t{created_at}\t{updated_at}\n"

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

    # --sort_by 需要全量拉取才能排序
    has_custom_filter = args.sort_by is not None

    if has_custom_filter:
        # 全量拉取 + 排序 + 截取
        all_items = []
        marker = ""
        while True:
            request = ListVpnUserGroupsRequest()
            request.vpn_server_id = args.vpn_server_id
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_vpn_user_groups(request)
            items = response.user_groups
            if not items:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_items and getattr(items[0], 'id', None) == getattr(all_items[-1], 'id', None):
                break
            all_items.extend(items)
            page_info = getattr(response, 'page_info', None)
            next_marker = getattr(page_info, 'next_marker', None) if page_info else None
            if next_marker is None:
                break
            marker = next_marker

        if not all_items:
            print(f"没有找到 VPN 用户组 (区域: {Region}, VPN 服务端 ID: {args.vpn_server_id})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'user_number':
                all_items.sort(key=lambda f: int(getattr(f, 'user_number', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 只查1次
        request = ListVpnUserGroupsRequest()
        request.vpn_server_id = args.vpn_server_id
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_vpn_user_groups(request)
        items = response.user_groups

        if not items:
            print(f"没有找到 VPN 用户组 (区域: {Region}, VPN 服务端 ID: {args.vpn_server_id})")
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
    print(f"vpn.list_vpn_user_groups 查询失败: {e}")
    exit(1)
