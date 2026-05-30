import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListConnectionMonitorsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 连接监控列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_connection_id", type=str, help="VPN 连接 ID，可通过 list_vpn_connections.py 获取")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID，可指定多个（逗号分隔），可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染连接监控列表
    :param items: 连接监控列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到连接监控")
        return

    output = f"id\tstatus\tvpn_connection_id\ttype\tsource_ip\tdestination_ip\tproto_type\n"
    for item in items:
        id = getattr(item, 'id', '')
        status = getattr(item, 'status', '')
        vpn_connection_id = getattr(item, 'vpn_connection_id', '')
        type_ = getattr(item, 'type', '')
        source_ip = getattr(item, 'source_ip', '')
        destination_ip = getattr(item, 'destination_ip', '')
        proto_type = getattr(item, 'proto_type', '')
        output += f"{id}\t{status}\t{vpn_connection_id}\t{type_}\t{source_ip}\t{destination_ip}\t{proto_type}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vpn_connection_id / --enterprise_project_id 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vpn_connection_id / --enterprise_project_id 参数缩小查询范围"
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
    request = ListConnectionMonitorsRequest()
    if args.vpn_connection_id:
        request.vpn_connection_id = args.vpn_connection_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id.split(',')
    response = client.list_connection_monitors(request)
    items = response.connection_monitors

    if not items:
        print(f"没有找到连接监控 (区域: {Region})")
        exit(0)

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
    print(f"vpn.list_connection_monitors 查询失败: {e}")
    exit(1)
