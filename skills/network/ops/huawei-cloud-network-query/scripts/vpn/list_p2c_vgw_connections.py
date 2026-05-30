import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListP2cVgwConnectionsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限（SDK 未说明上限，保守设定）

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 P2C VPN 网关连接列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--p2c_vgw_id", type=str, required=True, help="P2C VPN 网关 ID，可通过 list_p2c_vgws.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: inbound_packets, outbound_packets, inbound_bytes, outbound_bytes；方向可选: asc(升序), desc(降序)。例如 inbound_bytes:desc 表示按入站流量降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by inbound_bytes:desc --top 5 查找入站流量最大的 5 个连接")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by inbound_bytes:desc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('inbound_packets', 'outbound_packets', 'inbound_bytes', 'outbound_bytes') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: inbound_packets, outbound_packets, inbound_bytes, outbound_bytes；方向可选: asc, desc。例如 inbound_bytes:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染 P2C VPN 网关连接列表
    :param items: 连接列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 P2C VPN 网关连接")
        return

    output = f"connection_id\tclient_virtual_ip\tclient_ip\tclient_user_name\tinbound_packets\toutbound_packets\tinbound_bytes\toutbound_bytes\tconnection_established_time\ttimestamp\n"
    for item in items:
        connection_id = getattr(item, 'connection_id', '')
        client_virtual_ip = getattr(item, 'client_virtual_ip', '')
        client_ip = getattr(item, 'client_ip', '')
        client_user_name = getattr(item, 'client_user_name', '')
        inbound_packets = getattr(item, 'inbound_packets', '')
        outbound_packets = getattr(item, 'outbound_packets', '')
        inbound_bytes = getattr(item, 'inbound_bytes', '')
        outbound_bytes = getattr(item, 'outbound_bytes', '')
        connection_established_time = getattr(item, 'connection_established_time', '')
        timestamp = getattr(item, 'timestamp', '')
        output += f"{connection_id}\t{client_virtual_ip}\t{client_ip}\t{client_user_name}\t{inbound_packets}\t{outbound_packets}\t{inbound_bytes}\t{outbound_bytes}\t{connection_established_time}\t{timestamp}\n"

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
        sdk_offset = 0
        while True:
            request = ListP2cVgwConnectionsRequest()
            request.p2c_vgw_id = args.p2c_vgw_id
            request.limit = API_LIMIT
            request.offset = sdk_offset
            response = client.list_p2c_vgw_connections(request)
            items = response.connections
            if not items:
                break
            all_items.extend(items)
            total_count = getattr(response, 'total_count', None)
            if total_count is not None:
                if sdk_offset + len(items) >= total_count:
                    break
            else:
                if len(items) < API_LIMIT:
                    break
            sdk_offset += len(items)

        if not all_items:
            print(f"没有找到 P2C VPN 网关连接 (区域: {Region}, P2C VPN 网关 ID: {args.p2c_vgw_id})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'inbound_packets':
                all_items.sort(key=lambda f: int(getattr(f, 'inbound_packets', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'outbound_packets':
                all_items.sort(key=lambda f: int(getattr(f, 'outbound_packets', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'inbound_bytes':
                all_items.sort(key=lambda f: int(getattr(f, 'inbound_bytes', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'outbound_bytes':
                all_items.sort(key=lambda f: int(getattr(f, 'outbound_bytes', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # API 使用 offset 分页（无 marker），用 offset 实现服务端分页，对外暴露 --marker
        # marker 值为 offset 数值（字符串形式）
        sdk_offset = 0
        if args.marker:
            try:
                sdk_offset = int(args.marker)
            except ValueError:
                sdk_offset = 0

        request = ListP2cVgwConnectionsRequest()
        request.p2c_vgw_id = args.p2c_vgw_id
        request.limit = FETCH_SIZE
        request.offset = sdk_offset

        response = client.list_p2c_vgw_connections(request)
        items = response.connections

        if not items:
            print(f"没有找到 P2C VPN 网关连接 (区域: {Region}, P2C VPN 网关 ID: {args.p2c_vgw_id})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        total_count = getattr(response, 'total_count', None)
        next_marker = None
        if total_count is not None:
            has_more = (sdk_offset + total_count) > PAGE_SIZE and len(items) > PAGE_SIZE
            if total_count > sdk_offset + PAGE_SIZE:
                has_more = True
            else:
                has_more = False
        else:
            has_more = len(items) > PAGE_SIZE

        if has_more:
            next_marker = str(sdk_offset + PAGE_SIZE)

        # 只展示前 PAGE_SIZE 条
        display_items = items[:PAGE_SIZE]

        # 渲染结果
        render(display_items, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_p2c_vgw_connections 查询失败: {e}")
    exit(1)
