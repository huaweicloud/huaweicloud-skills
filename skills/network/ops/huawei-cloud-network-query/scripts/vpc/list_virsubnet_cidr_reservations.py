import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListVirsubnetCidrReservationsRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询子网CIDR保留列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="CIDR 保留 ID 过滤，支持多个")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="子网 ID 过滤，支持多个，可通过 list_virsubnets.py 获取")
parser.add_argument("--cidr", type=str, nargs="+", help="CIDR 网段过滤，支持多个")
parser.add_argument("--ip_version", type=int, nargs="+", help="IP 版本过滤(4=IPv4,6=IPv6)，支持多个")
parser.add_argument("--name", type=str, nargs="+", help="名称过滤，支持多个")
parser.add_argument("--description", type=str, nargs="+", help="描述过滤，支持多个")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID 过滤，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染子网CIDR保留列表
    :param items: CIDR保留列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到子网CIDR保留")
        return

    output = f"id\tvirsubnet_id\tvpc_id\tcidr\tip_version\tname\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        vpc_id = getattr(item, 'vpc_id', '')
        cidr = getattr(item, 'cidr', '')
        ip_version = getattr(item, 'ip_version', '')
        name = getattr(item, 'name', '')
        description = getattr(item, 'description', '')
        output += f"{id}\t{virsubnet_id}\t{vpc_id}\t{cidr}\t{ip_version}\t{name}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条子网CIDR保留，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --virsubnet_id / --cidr 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --virsubnet_id / --cidr 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --virsubnet_id / --cidr 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --virsubnet_id / --cidr 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条子网CIDR保留"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListVirsubnetCidrReservationsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.cidr:
        request.cidr = args.cidr
    if args.ip_version:
        request.ip_version = args.ip_version
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    # 只做一次查询
    response = client.list_virsubnet_cidr_reservations(request)
    items = response.virsubnet_cidr_reservations

    if not items:
        print(f"没有找到子网CIDR保留 (区域: {Region})")
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
            next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_virsubnet_cidr_reservations 查询失败: {e}")
    exit(1)
