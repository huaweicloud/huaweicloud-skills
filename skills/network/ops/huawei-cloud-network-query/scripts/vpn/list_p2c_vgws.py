import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListP2cVgwsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 P2C VPN 网关列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="P2C VPN 网关名称，用于从结果中按名称模糊过滤（自定义过滤，需全量拉取）")
parser.add_argument("--status", type=str, help="P2C VPN 网关状态，用于从结果中按状态过滤（如 ACTIVE）（自定义过滤，需全量拉取）")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: max_connection_number, current_connection_number；方向可选: asc(升序), desc(降序)。例如 max_connection_number:asc 表示按最大连接数升序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by max_connection_number:asc --top 5 查找最大连接数最小的 5 个 P2C VPN 网关")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by max_connection_number:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('max_connection_number', 'current_connection_number') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: max_connection_number, current_connection_number；方向可选: asc, desc。例如 max_connection_number:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 P2C VPN 网关列表
    :param items: 网关列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 P2C VPN 网关")
        return

    output = f"id\tname\tstatus\tvpc_id\tconnect_subnet\tflavor\teip_id\teip_address\tmax_connection_number\tcurrent_connection_number\tenterprise_project_id\tcreated_at\tupdated_at\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        status = getattr(item, 'status', '')
        vpc_id = getattr(item, 'vpc_id', '')
        connect_subnet = getattr(item, 'connect_subnet', '')
        flavor = getattr(item, 'flavor', '')
        eip_info = getattr(item, 'eip', None)
        eip_id = getattr(eip_info, 'id', '') if eip_info else ''
        eip_address = getattr(eip_info, 'ip_address', '') if eip_info else ''
        max_connection_number = getattr(item, 'max_connection_number', '')
        current_connection_number = getattr(item, 'current_connection_number', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        output += f"{id}\t{name}\t{status}\t{vpc_id}\t{connect_subnet}\t{flavor}\t{eip_id}\t{eip_address}\t{max_connection_number}\t{current_connection_number}\t{enterprise_project_id}\t{created_at}\t{updated_at}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status 参数缩小查询范围"
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

    # --name 和 --status 是自定义过滤参数（SDK Request 无 name/status 字段），需要全量拉取+本地过滤
    has_custom_filter = args.name is not None or args.status is not None or args.sort_by is not None

    if has_custom_filter:
        # 全量拉取 + 本地过滤（因为SDK单次最多返回有限条数，必须循环拉完）
        all_items = []
        marker = ""
        while True:
            request = ListP2cVgwsRequest()
            request.limit = 1000
            if marker:
                request.marker = marker
            response = client.list_p2c_vgws(request)
            items = response.p2c_vpn_gateways
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
            print(f"没有找到 P2C VPN 网关 (区域: {Region})")
            exit(0)

        # 本地过滤
        filtered_items = all_items
        if args.name:
            filtered_items = [item for item in filtered_items if args.name in getattr(item, 'name', '')]
        if args.status:
            filtered_items = [item for item in filtered_items if getattr(item, 'status', '') == args.status]

        if not filtered_items:
            print(f"没有找到 P2C VPN 网关 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'max_connection_number':
                filtered_items.sort(key=lambda f: int(getattr(f, 'max_connection_number', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'current_connection_number':
                filtered_items.sort(key=lambda f: int(getattr(f, 'current_connection_number', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            filtered_items = filtered_items[:args.top]

        # 渲染过滤结果（全量已拉取，无需翻页）
        render(filtered_items, total_count=len(filtered_items))
    else:
        # 正常逻辑：只查1次
        request = ListP2cVgwsRequest()
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_p2c_vgws(request)
        items = response.p2c_vpn_gateways

        if not items:
            print(f"没有找到 P2C VPN 网关 (区域: {Region})")
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
    print(f"vpn.list_p2c_vgws 查询失败: {e}")
    exit(1)
