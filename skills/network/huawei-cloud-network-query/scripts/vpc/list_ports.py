import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListPortsRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询端口列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="端口 ID 过滤，支持多个")
parser.add_argument("--name", type=str, nargs="+", help="端口名称过滤，支持多个")
parser.add_argument("--status", type=str, help="端口状态过滤(ACTIVE/BUILD/DOWN)")
parser.add_argument("--admin_state_up", type=bool, help="管理状态过滤(true/false)")
parser.add_argument("--vpc_id", type=str, nargs="+", help="VPC ID 过滤，支持多个，可通过 list_vpcs.py 获取")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="虚拟子网 ID 过滤，支持多个，可通过 list_virsubnets.py 获取")
parser.add_argument("--device_id", type=str, nargs="+", help="设备 ID 过滤，支持多个")
parser.add_argument("--device_owner", type=str, nargs="+", help="设备名称过滤，支持多个")
parser.add_argument("--mac_address", type=str, nargs="+", help="MAC 地址过滤，支持多个")
parser.add_argument("--private_ips", type=str, nargs="+", help="私有 IP 过滤，支持多个")
parser.add_argument("--security_groups", type=str, nargs="+", help="安全组 ID 过滤，支持多个")
parser.add_argument("--instance_id", type=str, help="云服务实例 ID 过滤")
parser.add_argument("--instance_type", type=str, help="云服务实例类型过滤")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染端口列表
    :param items: 端口列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到端口")
        return

    output = f"id\tname\tdevice_id\tdevice_owner\tmac_address\tstatus\tadmin_state_up\tvpc_id\tvirsubnet_id\tinstance_id\tinstance_type\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        device_id = getattr(item, 'device_id', '')
        device_owner = getattr(item, 'device_owner', '')
        mac_address = getattr(item, 'mac_address', '')
        status = getattr(item, 'status', '')
        admin_state_up = getattr(item, 'admin_state_up', '')
        vpc_id = getattr(item, 'vpc_id', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        instance_id = getattr(item, 'instance_id', '')
        instance_type = getattr(item, 'instance_type', '')
        output += f"{id}\t{name}\t{device_id}\t{device_owner}\t{mac_address}\t{status}\t{admin_state_up}\t{vpc_id}\t{virsubnet_id}\t{instance_id}\t{instance_type}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条端口，当前返回 {showing_count} 条"
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
        output += f"\n共 {showing_count} 条端口"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListPortsRequest()
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.device_id:
        request.device_id = args.device_id
    if args.device_owner:
        request.device_owner = args.device_owner
    if args.mac_address:
        request.mac_address = args.mac_address
    if args.private_ips:
        request.private_ips = args.private_ips
    if args.security_groups:
        request.security_groups = args.security_groups
    if args.instance_id:
        request.instance_id = args.instance_id
    if args.instance_type:
        request.instance_type = args.instance_type
    response = client.list_ports(request)
    items = response.ports

    if not items:
        print(f"没有找到端口 (区域: {Region})")
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
    print(f"vpc.list_ports 查询失败: {e}")
    exit(1)
