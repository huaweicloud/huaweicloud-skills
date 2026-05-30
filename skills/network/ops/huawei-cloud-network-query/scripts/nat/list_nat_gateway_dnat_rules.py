import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListNatGatewayDnatRulesRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网NAT网关DNAT规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--nat_gateway_id", type=str, nargs="+", help="公网NAT网关ID，可多选，可通过 list_nat_gateways.py 获取")
parser.add_argument("--id", type=str, help="DNAT规则ID，精确过滤")
parser.add_argument("--protocol", type=str, nargs="+", choices=["tcp", "TCP", "udp", "UDP", "any", "ANY"], help="协议类型，可多选，如: --protocol tcp udp")
parser.add_argument("--floating_ip_id", type=str, help="弹性公网IP的ID")
parser.add_argument("--floating_ip_address", type=str, help="弹性公网IP地址")
parser.add_argument("--global_eip_id", type=str, help="全域弹性公网IP的ID")
parser.add_argument("--global_eip_address", type=str, help="全域弹性公网IP地址")
parser.add_argument("--status", type=str, nargs="+", choices=["ACTIVE", "PENDING_CREATE", "PENDING_UPDATE", "PENDING_DELETE", "EIP_FREEZED", "INACTIVE"], help="DNAT规则状态，可多选")
parser.add_argument("--admin_state_up", type=str, choices=["true", "false"], help="解冻/冻结状态: true=解冻 false=冻结")
parser.add_argument("--internal_service_port", type=int, help="内部服务端口号，0~65535")
parser.add_argument("--external_service_port", type=int, help="外部服务端口号，0~65535")
parser.add_argument("--port_id", type=str, help="虚拟机或裸机的Port ID，对应虚拟私有云场景，与private_ip参数二选一")
parser.add_argument("--private_ip", type=str, help="用户私有IP地址，对应专线、云连接场景，与port_id参数二选一")
parser.add_argument("--description", type=str, help="DNAT规则描述，精确过滤")
parser.add_argument("--created_at", type=str, help="DNAT规则创建时间过滤，格式: yyyy-mm-ddThh:mm:ssZ")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: internal_service_port, external_service_port；方向可选: asc(升序), desc(降序)。例如 internal_service_port:asc 表示按内部服务端口升序，external_service_port:desc 表示按外部服务端口降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by internal_service_port:asc --top 5 查找内部服务端口最小的 5 条 DNAT 规则")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by internal_service_port:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('internal_service_port', 'external_service_port') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: internal_service_port, external_service_port；方向可选: asc, desc。例如 internal_service_port:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染DNAT规则列表
    :param items: DNAT规则列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 DNAT 规则")
        return

    output = f"id\tstatus\tprotocol\tfloating_ip_address\tinternal_service_port\tprivate_ip\texternal_service_port\tnat_gateway_id\tfloating_ip_id\tport_id\tglobal_eip_id\tglobal_eip_address\tinternal_service_port_range\texternal_service_port_range\tcreated_at\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        status = getattr(item, 'status', '')
        protocol = getattr(item, 'protocol', '')
        floating_ip_address = getattr(item, 'floating_ip_address', '')
        internal_service_port = getattr(item, 'internal_service_port', '')
        private_ip = getattr(item, 'private_ip', '')
        external_service_port = getattr(item, 'external_service_port', '')
        nat_gateway_id = getattr(item, 'nat_gateway_id', '')
        floating_ip_id = getattr(item, 'floating_ip_id', '')
        port_id = getattr(item, 'port_id', '')
        global_eip_id = getattr(item, 'global_eip_id', '')
        global_eip_address = getattr(item, 'global_eip_address', '')
        internal_service_port_range = getattr(item, 'internal_service_port_range', '')
        external_service_port_range = getattr(item, 'external_service_port_range', '')
        created_at = getattr(item, 'created_at', '')
        description = getattr(item, 'description', '')
        output += f"{id}\t{status}\t{protocol}\t{floating_ip_address}\t{internal_service_port}\t{private_ip}\t{external_service_port}\t{nat_gateway_id}\t{floating_ip_id}\t{port_id}\t{global_eip_id}\t{global_eip_address}\t{internal_service_port_range}\t{external_service_port_range}\t{created_at}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个 DNAT 规则，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --nat_gateway_id / --id / --status / --protocol 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --nat_gateway_id / --id / --status / --protocol 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --nat_gateway_id / --id / --status / --protocol 等参数缩小查询范围"
        else:
            output += f"\n可使用 --nat_gateway_id / --id / --status / --protocol 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个 DNAT 规则"

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
    request = ListNatGatewayDnatRulesRequest()
    if args.marker:
        request.marker = args.marker
    if args.nat_gateway_id:
        request.nat_gateway_id = args.nat_gateway_id
    if args.id:
        request.id = args.id
    if args.protocol:
        request.protocol = args.protocol
    if args.floating_ip_id:
        request.floating_ip_id = args.floating_ip_id
    if args.floating_ip_address:
        request.floating_ip_address = args.floating_ip_address
    if args.global_eip_id:
        request.global_eip_id = args.global_eip_id
    if args.global_eip_address:
        request.global_eip_address = args.global_eip_address
    if args.status:
        request.status = args.status
    if args.admin_state_up:
        request.admin_state_up = args.admin_state_up == "true"
    if args.internal_service_port is not None:
        request.internal_service_port = args.internal_service_port
    if args.external_service_port is not None:
        request.external_service_port = args.external_service_port
    if args.port_id:
        request.port_id = args.port_id
    if args.private_ip:
        request.private_ip = args.private_ip
    if args.description:
        request.description = args.description
    if args.created_at:
        request.created_at = args.created_at

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_items = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_nat_gateway_dnat_rules(request)
            items = response.dnat_rules
            if not items:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_items and getattr(items[0], 'id', None) == getattr(all_items[-1], 'id', None):
                break
            all_items.extend(items)
            if len(items) < API_LIMIT:
                break
            marker = items[-1].id
            if not marker:
                break

        if not all_items:
            print(f"没有找到 DNAT 规则 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'internal_service_port':
                all_items.sort(key=lambda f: int(getattr(f, 'internal_service_port', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'external_service_port':
                all_items.sort(key=lambda f: int(getattr(f, 'external_service_port', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE

        # 只做一次查询
        response = client.list_nat_gateway_dnat_rules(request)
        items = response.dnat_rules

        if not items:
            print(f"没有找到 DNAT 规则 (区域: {Region})")
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
    print(f"nat.list_nat_gateway_dnat_rules 查询失败: {e}")
    exit(1)
