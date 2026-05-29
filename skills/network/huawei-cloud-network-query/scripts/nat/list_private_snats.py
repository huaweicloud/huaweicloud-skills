import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListPrivateSnatsRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询私网NAT网关SNAT规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--gateway_id", type=str, nargs="+", help="私网NAT网关ID，可多选，可通过 list_private_nats.py 获取")
parser.add_argument("--id", type=str, nargs="+", help="SNAT规则ID，可多选")
parser.add_argument("--description", type=str, nargs="+", help="SNAT规则描述，可多选")
parser.add_argument("--cidr", type=str, nargs="+", help="规则匹配的CIDR，可多选")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="规则匹配的子网ID，可多选")
parser.add_argument("--transit_ip_id", type=str, nargs="+", help="中转IP的ID，可多选，可通过 list_transit_ip.py 获取")
parser.add_argument("--transit_ip_address", type=str, nargs="+", help="中转IP地址，可多选")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目ID，可多选，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染私网SNAT规则列表
    :param items: SNAT规则列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到私网 SNAT 规则")
        return

    output = f"id\tgateway_id\tcidr\tvirsubnet_id\ttransit_ip_associations\tenterprise_project_id\tstatus\tcreated_at\tupdated_at\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        gateway_id = getattr(item, 'gateway_id', '')
        cidr = getattr(item, 'cidr', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        transit_ip_associations = getattr(item, 'transit_ip_associations', [])
        transit_str = ';'.join([f"{getattr(a,'transit_ip_id','')}:{getattr(a,'transit_ip_address','')}" for a in transit_ip_associations]) if transit_ip_associations else ''
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        status = getattr(item, 'status', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        description = getattr(item, 'description', '')
        output += f"{id}\t{gateway_id}\t{cidr}\t{virsubnet_id}\t{transit_str}\t{enterprise_project_id}\t{status}\t{created_at}\t{updated_at}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个私网 SNAT 规则，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --gateway_id / --id / --cidr 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --gateway_id / --id / --cidr 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --gateway_id / --id / --cidr 等参数缩小查询范围"
        else:
            output += f"\n可使用 --gateway_id / --id / --cidr 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个私网 SNAT 规则"

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
    request = ListPrivateSnatsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.gateway_id:
        request.gateway_id = args.gateway_id
    if args.id:
        request.id = args.id
    if args.description:
        request.description = args.description
    if args.cidr:
        request.cidr = args.cidr
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.transit_ip_id:
        request.transit_ip_id = args.transit_ip_id
    if args.transit_ip_address:
        request.transit_ip_address = args.transit_ip_address
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    # 只做一次查询
    response = client.list_private_snats(request)
    items = response.snat_rules

    if not items:
        print(f"没有找到私网 SNAT 规则 (区域: {Region})")
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
    print(f"nat.list_private_snats 查询失败: {e}")
    exit(1)
