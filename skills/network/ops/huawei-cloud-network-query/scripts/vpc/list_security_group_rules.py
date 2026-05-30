import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListSecurityGroupRulesRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询安全组规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--security_group_id", type=str, required=True, help="安全组 ID（必填），可通过 list_security_groups.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="安全组规则 ID 过滤，支持多个")
parser.add_argument("--direction", type=str, help="规则方向过滤(ingress/egress)")
parser.add_argument("--protocol", type=str, nargs="+", help="协议过滤，支持多个(tcp/udp/icmp等)")
parser.add_argument("--action", type=str, help="生效策略过滤(allow/deny)")
parser.add_argument("--ethertype", type=str, nargs="+", help="IP协议类型过滤(IPv4/IPv6)")
parser.add_argument("--remote_ip_prefix", type=str, help="远端IP地址过滤(cidr格式)")
parser.add_argument("--remote_group_id", type=str, nargs="+", help="远端安全组 ID 过滤，支持多个")
parser.add_argument("--remote_address_group_id", type=str, nargs="+", help="远端地址组 ID 过滤，支持多个")
parser.add_argument("--priority", type=int, nargs="+", help="优先级过滤，支持多个(1-100)")
parser.add_argument("--enabled", type=bool, help="是否启用过滤(true/false)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: priority；方向可选: asc(升序), desc(降序)。例如 priority:asc 表示按优先级升序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by priority:asc --top 5 查找优先级最高的 5 条规则")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by priority:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('priority',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: priority；方向可选: asc, desc。例如 priority:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染安全组规则列表
    :param items: 安全组规则列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到安全组规则")
        return

    output = f"id\tdirection\tprotocol\tethertype\tmultiport\taction\tpriority\tremote_ip_prefix\tremote_group_id\tremote_address_group_id\tenabled\n"
    for item in items:
        id = getattr(item, 'id', '')
        direction = getattr(item, 'direction', '')
        protocol = getattr(item, 'protocol', '')
        ethertype = getattr(item, 'ethertype', '')
        multiport = getattr(item, 'multiport', '')
        action = getattr(item, 'action', '')
        priority = getattr(item, 'priority', '')
        remote_ip_prefix = getattr(item, 'remote_ip_prefix', '')
        remote_group_id = getattr(item, 'remote_group_id', '')
        remote_address_group_id = getattr(item, 'remote_address_group_id', '')
        enabled = getattr(item, 'enabled', '')
        output += f"{id}\t{direction}\t{protocol}\t{ethertype}\t{multiport}\t{action}\t{priority}\t{remote_ip_prefix}\t{remote_group_id}\t{remote_address_group_id}\t{enabled}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条安全组规则，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --direction / --protocol 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --direction / --protocol 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --direction / --protocol 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --direction / --protocol 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条安全组规则"

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
    request = ListSecurityGroupRulesRequest()
    request.security_group_id = [args.security_group_id]
    if args.id:
        request.id = args.id
    if args.direction:
        request.direction = args.direction
    if args.protocol:
        request.protocol = args.protocol
    if args.action:
        request.action = args.action
    if args.ethertype:
        request.ethertype = args.ethertype
    if args.remote_ip_prefix:
        request.remote_ip_prefix = args.remote_ip_prefix
    if args.remote_group_id:
        request.remote_group_id = args.remote_group_id
    if args.remote_address_group_id:
        request.remote_address_group_id = args.remote_address_group_id
    if args.priority:
        request.priority = args.priority
    if args.enabled is not None:
        request.enabled = args.enabled

    # --sort_by 需要全量拉取才能排序
    has_custom_filter = args.sort_by is not None

    if has_custom_filter:
        # 全量拉取 + 排序 + 截取
        all_items = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_security_group_rules(request)
            items = response.security_group_rules
            if not items:
                break
            # 检测重复数据
            if marker and all_items and getattr(items[0], 'id', None) == getattr(all_items[-1], 'id', None):
                break
            all_items.extend(items)
            page_info = getattr(response, 'page_info', None)
            next_marker_val = getattr(page_info, 'next_marker', None) if page_info else None
            if not next_marker_val:
                break
            marker = next_marker_val

        if not all_items:
            print(f"没有找到安全组规则 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'priority':
                all_items.sort(key=lambda r: int(getattr(r, 'priority', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 正常逻辑：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_security_group_rules(request)
        items = response.security_group_rules

        if not items:
            print(f"没有找到安全组规则 (区域: {Region})")
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
    print(f"vpc.list_security_group_rules 查询失败: {e}")
    exit(1)
