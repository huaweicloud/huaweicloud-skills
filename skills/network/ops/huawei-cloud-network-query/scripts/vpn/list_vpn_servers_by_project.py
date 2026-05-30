import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListVpnServersByProjectRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询项目下 VPN 服务端列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--status", type=str, help="VPN 服务端状态，用于从结果中按状态过滤（如 ACTIVE）（自定义过滤，需全量拉取）")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 VPN 服务端列表
    :param items: 服务端列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 VPN 服务端")
        return

    output = f"id\tp2c_vgw_id\tclient_cidr\tclient_auth_type\ttunnel_protocol\tstatus\tcreated_at\tupdated_at\n"
    for item in items:
        id = getattr(item, 'id', '')
        p2c_vgw_id = getattr(item, 'p2c_vgw_id', '')
        client_cidr = getattr(item, 'client_cidr', '')
        client_auth_type = getattr(item, 'client_auth_type', '')
        tunnel_protocol = getattr(item, 'tunnel_protocol', '')
        status = getattr(item, 'status', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        output += f"{id}\t{p2c_vgw_id}\t{client_cidr}\t{client_auth_type}\t{tunnel_protocol}\t{status}\t{created_at}\t{updated_at}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --status 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --status 参数缩小查询范围"
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

    # --status 是自定义过滤参数（SDK Request 无 status 字段），需要全量拉取+本地过滤
    has_custom_filter = args.status is not None

    if has_custom_filter:
        # 全量拉取 + 本地过滤（因为SDK单次最多返回有限条数，必须循环拉完）
        all_items = []
        marker = ""
        while True:
            request = ListVpnServersByProjectRequest()
            request.limit = 1000
            if marker:
                request.marker = marker
            response = client.list_vpn_servers_by_project(request)
            items = response.vpn_servers
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
            print(f"没有找到 VPN 服务端 (区域: {Region})")
            exit(0)

        # 本地过滤
        filtered_items = [item for item in all_items if getattr(item, 'status', '') == args.status]

        if not filtered_items:
            print(f"没有找到 VPN 服务端 (区域: {Region}, 状态过滤: {args.status})")
            exit(0)

        # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
        start_idx = 0
        if args.marker:
            for i, item in enumerate(filtered_items):
                if str(getattr(item, 'id', '')) == args.marker:
                    start_idx = i + 1
                    break

        remaining_items = filtered_items[start_idx:]
        if not remaining_items:
            print("没有更多数据")
            exit(0)

        # 判断是否还有更多数据
        has_more = len(remaining_items) > PAGE_SIZE
        next_marker_val = None
        if has_more:
            next_marker_val = str(getattr(remaining_items[PAGE_SIZE - 1], 'id', ''))
        display_items = remaining_items[:PAGE_SIZE]

        # 渲染结果
        render(display_items, total_count=len(filtered_items), has_more=has_more, next_marker=next_marker_val)
    else:
        # 正常逻辑：只查1次
        request = ListVpnServersByProjectRequest()
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_vpn_servers_by_project(request)
        items = response.vpn_servers

        if not items:
            print(f"没有找到 VPN 服务端 (区域: {Region})")
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
    print(f"vpn.list_vpn_servers_by_project 查询失败: {e}")
    exit(1)
