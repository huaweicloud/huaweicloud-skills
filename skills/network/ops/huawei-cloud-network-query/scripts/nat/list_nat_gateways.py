import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListNatGatewaysRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网NAT网关列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, help="公网NAT网关ID，精确过滤")
parser.add_argument("--name", type=str, help="公网NAT网关名称，支持模糊匹配")
parser.add_argument("--status", type=str, nargs="+", choices=["ACTIVE", "PENDING_CREATE", "PENDING_UPDATE", "PENDING_DELETE", "INACTIVE"], help="网关状态过滤，可多选，如: --status ACTIVE INACTIVE")
parser.add_argument("--spec", type=str, nargs="+", choices=["1", "2", "3", "4", "5"], help="网关规格过滤，可多选: 1=小型(1万) 2=中型(5万) 3=大型(20万) 4=超大型(100万) 5=企业型(1000万)")
parser.add_argument("--router_id", type=str, help="VPC ID，可通过 ../vpc/list_vpcs.py 获取")
parser.add_argument("--internal_network_id", type=str, help="公网NAT网关下行口（DVR的下一跳）所属的network ID")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID，可多选过滤，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--admin_state_up", type=str, choices=["true", "false"], help="解冻/冻结状态: true=解冻 false=冻结")
parser.add_argument("--description", type=str, help="公网NAT网关描述，精确过滤")
parser.add_argument("--created_at", type=str, help="公网NAT网关创建时间过滤，格式: yyyy-mm-ddThh:mm:ssZ (UTC时间)")
parser.add_argument("--sort_key", type=str, choices=["id", "name", "created_at", "status", "spec"], help="排序字段: id/name/created_at/status/spec")
parser.add_argument("--sort_dir", type=str, choices=["asc", "desc"], help="排序方向: asc=升序 desc=降序(默认)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: spec；方向可选: asc(升序), desc(降序)。spec 为网关规格(1=小型,2=中型,3=大型,4=超大型,5=企业型)。例如 spec:asc 表示按规格升序，spec:desc 表示按规格降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by spec:asc --top 5 查找规格最小的 5 个 NAT 网关，--sort_by spec:desc --top 3 查找规格最大的 3 个 NAT 网关")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by spec:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('spec',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: spec；方向可选: asc, desc。例如 spec:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染NAT网关列表
    :param items: NAT网关列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 NAT 网关")
        return

    output = f"id\tname\tstatus\tspec\trouter_id\tinternal_network_id\tngport_ip_address\tadmin_state_up\tcreated_at\tdescription\tenterprise_project_id\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        status = getattr(item, 'status', '')
        spec = getattr(item, 'spec', '')
        router_id = getattr(item, 'router_id', '')
        internal_network_id = getattr(item, 'internal_network_id', '')
        ngport_ip_address = getattr(item, 'ngport_ip_address', '')
        admin_state_up = getattr(item, 'admin_state_up', '')
        created_at = getattr(item, 'created_at', '')
        description = getattr(item, 'description', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        output += f"{id}\t{name}\t{status}\t{spec}\t{router_id}\t{internal_network_id}\t{ngport_ip_address}\t{admin_state_up}\t{created_at}\t{description}\t{enterprise_project_id}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 个 NAT 网关，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status / --spec 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --status / --spec 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status / --spec 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --status / --spec 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个 NAT 网关"

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
    request = ListNatGatewaysRequest()
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.spec:
        request.spec = args.spec
    if args.router_id:
        request.router_id = args.router_id
    if args.internal_network_id:
        request.internal_network_id = args.internal_network_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.admin_state_up:
        request.admin_state_up = args.admin_state_up == "true"
    if args.description:
        request.description = args.description
    if args.created_at:
        request.created_at = args.created_at
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_items = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_nat_gateways(request)
            items = response.nat_gateways
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
            print(f"没有找到 NAT 网关 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'spec':
                all_items.sort(key=lambda f: int(getattr(f, 'spec', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE

        # 只做一次查询
        response = client.list_nat_gateways(request)
        items = response.nat_gateways

        if not items:
            print(f"没有找到 NAT 网关 (区域: {Region})")
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
    print(f"nat.list_nat_gateways 查询失败: {e}")
    exit(1)
