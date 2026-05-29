import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListTransitIpsRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询中转IP列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, nargs="+", help="中转IP的ID，可多选")
parser.add_argument("--gateway_id", type=str, nargs="+", help="私网NAT网关ID，可多选，可通过 list_private_nats.py 获取")
parser.add_argument("--ip_address", type=str, nargs="+", help="中转IP地址，可多选")
parser.add_argument("--network_interface_id", type=str, nargs="+", help="中转IP的网络接口ID，可多选")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="当前租户子网的ID，可多选")
parser.add_argument("--transit_subnet_id", type=str, nargs="+", help="中转子网的ID，可多选，可通过 list_transit_subnet.py 获取")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目ID，可多选，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染中转IP列表
    :param items: 中转IP列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到中转 IP")
        return

    output = f"id\tip_address\tnetwork_interface_id\tgateway_id\tvirsubnet_id\ttransit_subnet_id\tenterprise_project_id\tstatus\tcreated_at\tupdated_at\ttags\n"
    for item in items:
        id = getattr(item, 'id', '')
        ip_address = getattr(item, 'ip_address', '')
        network_interface_id = getattr(item, 'network_interface_id', '')
        gateway_id = getattr(item, 'gateway_id', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        transit_subnet_id = getattr(item, 'transit_subnet_id', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        status = getattr(item, 'status', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        tags = getattr(item, 'tags', [])
        tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in tags]) if tags else ''
        output += f"{id}\t{ip_address}\t{network_interface_id}\t{gateway_id}\t{virsubnet_id}\t{transit_subnet_id}\t{enterprise_project_id}\t{status}\t{created_at}\t{updated_at}\t{tag_str}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个中转 IP，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --gateway_id / --ip_address 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --gateway_id / --ip_address 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --gateway_id / --ip_address 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --gateway_id / --ip_address 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个中转 IP"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListTransitIpsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.gateway_id:
        request.gateway_id = args.gateway_id
    if args.ip_address:
        request.ip_address = args.ip_address
    if args.network_interface_id:
        request.network_interface_id = args.network_interface_id
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.transit_subnet_id:
        request.transit_subnet_id = args.transit_subnet_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    # 只做一次查询
    response = client.list_transit_ips(request)
    items = response.transit_ips

    if not items:
        print(f"没有找到中转 IP (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 有 page_info，必须用 page_info.next_marker
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(items) > PAGE_SIZE
        if has_more:
            next_marker = str(items[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"nat.list_transit_ips 查询失败: {e}")
    exit(1)
