import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListTransitSubnetRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询中转子网列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, nargs="+", help="中转子网ID，可多选")
parser.add_argument("--name", type=str, nargs="+", help="中转子网名称，可多选")
parser.add_argument("--description", type=str, nargs="+", help="中转子网描述，可多选")
parser.add_argument("--vpc_id", type=str, nargs="+", help="中转子网所属VPC的ID，可多选，可通过 ../vpc/list_vpcs.py 获取")
parser.add_argument("--virsubnet_id", type=str, nargs="+", help="中转子网的子网ID，可多选")
parser.add_argument("--virsubnet_project_id", type=str, nargs="+", help="中转子网的子网所属项目ID，可多选")
parser.add_argument("--status", type=str, nargs="+", choices=["ACTIVE", "INACTIVE"], help="中转子网状态，可多选: ACTIVE=正常 INACTIVE=不可用")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: ip_count；方向可选: asc(升序), desc(降序)。ip_count 为中转子网的IP数量。例如 ip_count:asc 表示按IP数量升序，ip_count:desc 表示按IP数量降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by ip_count:asc --top 5 查找IP数量最少的 5 个中转子网")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by ip_count:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('ip_count',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: ip_count；方向可选: asc, desc。例如 ip_count:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染中转子网列表
    :param items: 中转子网列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到中转子网")
        return

    output = f"id\tname\tvpc_id\tvirsubnet_id\tcidr\ttype\tstatus\tip_count\tvirsubnet_project_id\tcreated_at\tupdated_at\ttags\tdescription\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        vpc_id = getattr(item, 'vpc_id', '')
        virsubnet_id = getattr(item, 'virsubnet_id', '')
        cidr = getattr(item, 'cidr', '')
        type_ = getattr(item, 'type', '')
        status = getattr(item, 'status', '')
        ip_count = getattr(item, 'ip_count', '')
        virsubnet_project_id = getattr(item, 'virsubnet_project_id', '')
        created_at = getattr(item, 'created_at', '')
        updated_at = getattr(item, 'updated_at', '')
        tags = getattr(item, 'tags', [])
        tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in tags]) if tags else ''
        description = getattr(item, 'description', '')
        output += f"{id}\t{name}\t{vpc_id}\t{virsubnet_id}\t{cidr}\t{type_}\t{status}\t{ip_count}\t{virsubnet_project_id}\t{created_at}\t{updated_at}\t{tag_str}\t{description}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个中转子网，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status / --vpc_id 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --status / --vpc_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status / --vpc_id 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --status / --vpc_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个中转子网"

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
    request = ListTransitSubnetRequest()
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.virsubnet_id:
        request.virsubnet_id = args.virsubnet_id
    if args.virsubnet_project_id:
        request.virsubnet_project_id = args.virsubnet_project_id
    if args.status:
        request.status = args.status

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_items = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_transit_subnet(request)
            items = response.transit_subnets
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
            print(f"没有找到中转子网 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'ip_count':
                all_items.sort(key=lambda f: int(getattr(f, 'ip_count', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE

        # 只做一次查询
        response = client.list_transit_subnet(request)
        items = response.transit_subnets

        if not items:
            print(f"没有找到中转子网 (区域: {Region})")
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
    print(f"nat.list_transit_subnet 查询失败: {e}")
    exit(1)
