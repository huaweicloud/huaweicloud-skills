import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListVgwsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 网关列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vgw_id", type=str, help="VPN 网关 ID，用于按 ID 过滤查询结果")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID，多个以逗号分隔，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--name", type=str, help="VPN 网关名称，用于从结果中按名称模糊过滤（自定义过滤，需全量拉取）")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: connection_number, used_connection_number；方向可选: asc(升序), desc(降序)。例如 connection_number:asc 表示按连接数升序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by connection_number:asc --top 5 查找连接数最小的 5 个 VPN 网关")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by connection_number:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('connection_number', 'used_connection_number') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: connection_number, used_connection_number；方向可选: asc, desc。例如 connection_number:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 VPN 网关列表
    :param items: 网关列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 VPN 网关")
        return

    output = f"id\tname\tstatus\tattachment_type\tip_version\tvpc_id\tflavor\teip1_address\tconnection_number\tused_connection_number\tha_mode\tenterprise_project_id\tcreated_at\tupdated_at\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        status = getattr(item, 'status', '')
        attachment_type = getattr(item, 'attachment_type', '')
        ip_version = getattr(item, 'ip_version', '')
        vpc_id = getattr(item, 'vpc_id', '')
        flavor = getattr(item, 'flavor', '')
        eip1_info = getattr(item, 'eip1', None)
        eip1_address = getattr(eip1_info, 'ip_address', '') if eip1_info else ''
        connection_number = getattr(item, 'connection_number', '')
        used_connection_number = getattr(item, 'used_connection_number', '')
        ha_mode = getattr(item, 'ha_mode', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        output += f"{id}\t{name}\t{status}\t{attachment_type}\t{ip_version}\t{vpc_id}\t{flavor}\t{eip1_address}\t{connection_number}\t{used_connection_number}\t{ha_mode}\t{enterprise_project_id}\t{created_at}\t{updated_at}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vgw_id / --name 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vgw_id / --name 参数缩小查询范围"
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

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListVgwsRequest()
    if args.vgw_id:
        request.vgw_id = args.vgw_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id.split(',')
    response = client.list_vgws(request)
    items = response.vpn_gateways

    if not items:
        print(f"没有找到 VPN 网关 (区域: {Region})")
        exit(0)

    # --name 是自定义过滤参数（SDK Request 无 name 字段）
    if args.name:
        items = [item for item in items if args.name in getattr(item, 'name', '')]

    if not items:
        print(f"没有找到 VPN 网关 (区域: {Region})")
        exit(0)

    # 客户端排序
    if args.sort_by:
        sort_field, sort_dir = args.sort_by.split(':')
        if sort_field == 'connection_number':
            items.sort(key=lambda f: int(getattr(f, 'connection_number', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'used_connection_number':
            items.sort(key=lambda f: int(getattr(f, 'used_connection_number', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            items = items[:args.top]

        # 渲染排序结果（全量数据已排序，无需翻页）
        render(items, total_count=len(items))
    else:
        # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
        start_idx = 0
        if args.marker:
            for i, item in enumerate(items):
                if str(getattr(item, 'id', '')) == args.marker:
                    start_idx = i + 1
                    break

        remaining_items = items[start_idx:]
        if not remaining_items:
            print("没有更多数据")
            exit(0)

        # 判断是否还有更多数据
        has_more = len(remaining_items) > PAGE_SIZE
        next_marker = None
        if has_more:
            next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'id', ''))
        display_items = remaining_items[:PAGE_SIZE]

        # 渲染结果
        render(display_items, total_count=len(items), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_vgws 查询失败: {e}")
    exit(1)
