import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListSubNetworkInterfacesRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询子网络接口列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="辅助弹性网卡 ID 过滤，支持多个")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="虚拟子网 ID 过滤，支持多个，可通过 list_virsubnets.py 获取")
parser.add_argument("--private_ip_address", type=str, nargs="+", help="私有 IPv4 地址过滤，支持多个")
parser.add_argument("--mac_address", type=str, nargs="+", help="MAC 地址过滤，支持多个")
parser.add_argument("--vpc_id", type=str, nargs="+", help="VPC ID 过滤，支持多个，可通过 list_vpcs.py 获取")
parser.add_argument("--description", type=str, nargs="+", help="描述过滤，支持多个")
parser.add_argument("--parent_id", type=str, nargs="+", help="宿主网卡 ID 过滤，支持多个")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染子网络接口列表
    :param items: 子网络接口列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到子网络接口")
        return

    output = f"id\tvirsubnet_id\tprivate_ip_address\tmac_address\tvpc_id\tparent_id\tstate\tinstance_id\tinstance_type\n"
    for item in items:
        id = getattr(item, 'id', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        private_ip_address = getattr(item, 'private_ip_address', '')
        mac_address = getattr(item, 'mac_address', '')
        vpc_id = getattr(item, 'vpc_id', '')
        parent_id = getattr(item, 'parent_id', '')
        state = getattr(item, 'state', '')
        instance_id = getattr(item, 'instance_id', '')
        instance_type = getattr(item, 'instance_type', '')
        output += f"{id}\t{virsubnet_id}\t{private_ip_address}\t{mac_address}\t{vpc_id}\t{parent_id}\t{state}\t{instance_id}\t{instance_type}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条子网络接口，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --virsubnet_id / --vpc_id 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --virsubnet_id / --vpc_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --virsubnet_id / --vpc_id 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --virsubnet_id / --vpc_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条子网络接口"

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
    request = ListSubNetworkInterfacesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.private_ip_address:
        request.private_ip_address = args.private_ip_address
    if args.mac_address:
        request.mac_address = args.mac_address
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.description:
        request.description = args.description
    if args.parent_id:
        request.parent_id = args.parent_id

    # 只做一次查询
    response = client.list_sub_network_interfaces(request)
    items = response.sub_network_interfaces

    if not items:
        print(f"没有找到子网络接口 (区域: {Region})")
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
    print(f"vpc.list_sub_network_interfaces 查询失败: {e}")
    exit(1)
