import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListNatGatewaySnatRulesRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网NAT网关SNAT规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--nat_gateway_id", type=str, nargs="+", help="公网NAT网关ID，可多选，可通过 list_nat_gateways.py 获取")
parser.add_argument("--id", type=str, help="SNAT规则ID，精确过滤")
parser.add_argument("--status", type=str, choices=["ACTIVE", "PENDING_CREATE", "PENDING_UPDATE", "PENDING_DELETE", "EIP_FREEZED", "INACTIVE"], help="SNAT规则状态过滤")
parser.add_argument("--admin_state_up", type=str, choices=["true", "false"], help="解冻/冻结状态: true=解冻 false=冻结")
parser.add_argument("--floating_ip_id", type=str, help="弹性公网IP的ID，多个用逗号分隔")
parser.add_argument("--floating_ip_address", type=str, help="弹性公网IP地址，多个用逗号分隔")
parser.add_argument("--global_eip_id", type=str, help="全域弹性公网IP的ID，多个用逗号分隔")
parser.add_argument("--global_eip_address", type=str, help="全域弹性公网IP地址，多个用逗号分隔")
parser.add_argument("--cidr", type=str, help="网段或主机格式，与network_id二选一。source_type=0时cidr必须是VPC子网网段的子集; source_type=1时cidr必须指定专线侧网段")
parser.add_argument("--network_id", type=str, help="规则使用的网络ID，与cidr二选一")
parser.add_argument("--source_type", type=int, choices=[0, 1], help="资源类型: 0=VPC侧(可指定network_id或cidr,默认) 1=专线侧(只能指定cidr)")
parser.add_argument("--description", type=str, help="SNAT规则描述，精确过滤")
parser.add_argument("--created_at", type=str, help="SNAT规则创建时间过滤，格式: yyyy-mm-ddThh:mm:ssZ")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染SNAT规则列表
    :param items: SNAT规则列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 SNAT 规则")
        return

    output = f"id\tstatus\tfloating_ip_address\tcidr\tsource_type\tnat_gateway_id\tnetwork_id\tfloating_ip_id\tglobal_eip_id\tglobal_eip_address\tfreezed_ip_address\tcreated_at\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        status = getattr(item, 'status', '')
        floating_ip_address = getattr(item, 'floating_ip_address', '')
        cidr = getattr(item, 'cidr', '')
        source_type = getattr(item, 'source_type', '')
        nat_gateway_id = getattr(item, 'nat_gateway_id', '')
        network_id = getattr(item, 'network_id', '')
        floating_ip_id = getattr(item, 'floating_ip_id', '')
        global_eip_id = getattr(item, 'global_eip_id', '')
        global_eip_address = getattr(item, 'global_eip_address', '')
        freezed_ip_address = getattr(item, 'freezed_ip_address', '')
        created_at = getattr(item, 'created_at', '')
        description = getattr(item, 'description', '')
        output += f"{id}\t{status}\t{floating_ip_address}\t{cidr}\t{source_type}\t{nat_gateway_id}\t{network_id}\t{floating_ip_id}\t{global_eip_id}\t{global_eip_address}\t{freezed_ip_address}\t{created_at}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个 SNAT 规则，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --nat_gateway_id / --id / --status / --cidr 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --nat_gateway_id / --id / --status / --cidr 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --nat_gateway_id / --id / --status / --cidr 等参数缩小查询范围"
        else:
            output += f"\n可使用 --nat_gateway_id / --id / --status / --cidr 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个 SNAT 规则"

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
    request = ListNatGatewaySnatRulesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.nat_gateway_id:
        request.nat_gateway_id = args.nat_gateway_id
    if args.id:
        request.id = args.id
    if args.status:
        request.status = args.status
    if args.admin_state_up:
        request.admin_state_up = args.admin_state_up == "true"
    if args.floating_ip_id:
        request.floating_ip_id = args.floating_ip_id
    if args.floating_ip_address:
        request.floating_ip_address = args.floating_ip_address
    if args.global_eip_id:
        request.global_eip_id = args.global_eip_id
    if args.global_eip_address:
        request.global_eip_address = args.global_eip_address
    if args.cidr:
        request.cidr = args.cidr
    if args.network_id:
        request.network_id = args.network_id
    if args.source_type is not None:
        request.source_type = args.source_type
    if args.description:
        request.description = args.description
    if args.created_at:
        request.created_at = args.created_at

    # 只做一次查询
    response = client.list_nat_gateway_snat_rules(request)
    items = response.snat_rules

    if not items:
        print(f"没有找到 SNAT 规则 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 无 page_info / count / total_count / total_number，通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(items) > PAGE_SIZE
    if has_more:
        next_marker = str(items[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"nat.list_nat_gateway_snat_rules 查询失败: {e}")
    exit(1)
