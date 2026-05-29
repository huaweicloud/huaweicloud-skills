import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ListSubnetsRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询子网列表（v2）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpc_id", type=str, help="VPC ID过滤，可通过 list_vpcs.py 获取")
parser.add_argument("--name_contains", type=str, help="子网名称模糊搜索(客户端过滤)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: available_ip_address_count；方向可选: asc(升序), desc(降序)。例如 available_ip_address_count:asc 表示按可用IP数量升序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by available_ip_address_count:asc --top 5 查找可用IP最少的 5 个子网")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by available_ip_address_count:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('available_ip_address_count',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: available_ip_address_count；方向可选: asc, desc。例如 available_ip_address_count:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染子网列表
    :param items: 子网列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到子网")
        return

    output = f"name\tid\tcidr\tgateway_ip\tvpc_id\tstatus\tavailability_zone\tdhcp_enable\tavailable_ip_address_count\n"
    for item in items:
        name = getattr(item, 'name', '')
        id = getattr(item, 'id', '')
        cidr = getattr(item, 'cidr', '')
        gateway_ip = getattr(item, 'gateway_ip', '')
        vpc_id = getattr(item, 'vpc_id', '')
        status = getattr(item, 'status', '')
        availability_zone = getattr(item, 'availability_zone', '')
        dhcp_enable = getattr(item, 'dhcp_enable', '')
        available_ip_address_count = getattr(item, 'available_ip_address_count', '')
        output += f"{name}\t{id}\t{cidr}\t{gateway_ip}\t{vpc_id}\t{status}\t{availability_zone}\t{dhcp_enable}\t{available_ip_address_count}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条子网，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vpc_id / --name_contains 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --vpc_id / --name_contains 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --vpc_id / --name_contains 等参数缩小查询范围"
        else:
            output += f"\n可使用 --vpc_id / --name_contains 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条子网"

    print(output)


try:
    http_config = build_http_config()
    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # name_contains 是自定义过滤参数（SDK 不支持），需要全量拉取 + 本地过滤
    has_custom_filter = args.name_contains is not None or args.sort_by is not None

    if has_custom_filter:
        # 全量拉取 + 本地过滤（因为 SDK 单次最多返回1000条，必须循环拉完）
        all_items = []
        marker = ""
        while True:
            request = ListSubnetsRequest()
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            if args.vpc_id:
                request.vpc_id = args.vpc_id
            response = client.list_subnets(request)
            items = response.subnets
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

        # 本地过滤
        if args.name_contains:
            filtered = [s for s in all_items if args.name_contains in (getattr(s, 'name', '') or '')]
        else:
            filtered = all_items
        if not filtered:
            if args.name_contains:
                print(f"没有找到名称包含 '{args.name_contains}' 的子网 (区域: {Region})")
            else:
                print(f"没有找到子网 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'available_ip_address_count':
                filtered.sort(key=lambda s: int(getattr(s, 'available_ip_address_count', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            filtered = filtered[:args.top]

        # 渲染过滤结果（全量已拉取，无需翻页）
        render(filtered, total_count=len(filtered))
    else:
        # 正常逻辑：只查1次
        request = ListSubnetsRequest()
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker
        if args.vpc_id:
            request.vpc_id = args.vpc_id

        # 只做一次查询
        response = client.list_subnets(request)
        items = response.subnets

        if not items:
            print(f"没有找到子网 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        # Response 无 page_info 和 count，通过多查的第 FETCH_SIZE 条判断
        next_marker = None
        has_more = len(items) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

        # 只展示前 PAGE_SIZE 条
        display_items = items[:PAGE_SIZE]

        render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_subnets 查询失败: {e}")
    exit(1)
