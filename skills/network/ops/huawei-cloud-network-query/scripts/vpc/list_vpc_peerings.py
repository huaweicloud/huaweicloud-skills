import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ListVpcPeeringsRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询VPC对等连接列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, help="对等连接 ID 过滤")
parser.add_argument("--name", type=str, help="对等连接名称过滤")
parser.add_argument("--status", type=str, help="状态过滤(PENDING_ACCEPTANCE/REJECTED/EXPIRED/DELETED/ACTIVE)")
parser.add_argument("--tenant_id", type=str, help="项目 ID 过滤")
parser.add_argument("--vpc_id", type=str, help="VPC ID 过滤，可通过 list_vpcs.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染VPC对等连接列表
    :param items: 对等连接列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到VPC对等连接")
        return

    output = f"id\tname\tstatus\trequest_vpc_id\trequest_tenant_id\taccept_vpc_id\taccept_tenant_id\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        status = getattr(item, 'status', '')
        request_vpc_info = getattr(item, 'request_vpc_info', None)
        accept_vpc_info = getattr(item, 'accept_vpc_info', None)
        request_vpc_id = getattr(request_vpc_info, 'vpc_id', '') if request_vpc_info else ''
        request_tenant_id = getattr(request_vpc_info, 'tenant_id', '') if request_vpc_info else ''
        accept_vpc_id = getattr(accept_vpc_info, 'vpc_id', '') if accept_vpc_info else ''
        accept_tenant_id = getattr(accept_vpc_info, 'tenant_id', '') if accept_vpc_info else ''
        description = getattr(item, 'description', '')
        output += f"{id}\t{name}\t{status}\t{request_vpc_id}\t{request_tenant_id}\t{accept_vpc_id}\t{accept_tenant_id}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条VPC对等连接，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --status 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --status 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条VPC对等连接"

    print(output)


try:
    http_config = build_http_config()
    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListVpcPeeringsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.tenant_id:
        request.tenant_id = args.tenant_id
    if args.vpc_id:
        request.vpc_id = args.vpc_id

    # 只做一次查询
    response = client.list_vpc_peerings(request)
    items = response.peerings

    if not items:
        print(f"没有找到VPC对等连接 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 无 page_info 和 count，通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(items) > PAGE_SIZE
    if has_more:
        next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_vpc_peerings 查询失败: {e}")
    exit(1)
