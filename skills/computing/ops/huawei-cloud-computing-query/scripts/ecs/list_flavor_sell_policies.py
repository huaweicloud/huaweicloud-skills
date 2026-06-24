import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListFlavorSellPoliciesRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 规格销售策略列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--flavor_id", type=str, help="规格 ID，可通过 list_flavors.py 获取")
parser.add_argument("--sell_mode", type=str, choices=["postPaid", "prePaid", "spot", "ri"], help="计费模式：postPaid-按需，prePaid-包年包月，spot-竞价，ri-预留实例")
parser.add_argument("--sell_status", type=str, choices=["available", "sellout"], help="销售状态：available-正常售卖，sellout-售罄")
parser.add_argument("--availability_zone_id", type=str, help="可用区 ID，可通过 list_server_az_info.py 获取")
parser.add_argument("--longest_spot_duration_hours_gt", type=int, help="查询竞价实例时长大于此值的策略")
parser.add_argument("--largest_spot_duration_count_gt", type=int, help="查询竞价实例时长个数大于此值的策略")
parser.add_argument("--longest_spot_duration_hours", type=int, help="查询竞价实例时长等于此值的策略")
parser.add_argument("--largest_spot_duration_count", type=int, help="查询竞价实例时长个数等于此值的策略")
parser.add_argument("--interruption_policy", type=str, choices=["immediate", "delay"], help="中断策略：immediate-立即释放，delay-延迟释放")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: spot_duration_hours, spot_duration_count；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by spot_duration_hours:desc --top 5 查找竞价时长最长的 5 个策略")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by spot_duration_hours:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('spot_duration_hours', 'spot_duration_count') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: spot_duration_hours, spot_duration_count；方向可选: asc, desc。例如 spot_duration_hours:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（排序需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(policies, total_count=None, has_more=False, next_marker=None):
    """
    渲染策略列表
    :param policies: 策略列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not policies:
        print("没有找到 ECS 规格销售策略")
        return

    output = f"id\tflavor_id\tsell_mode\tsell_status\tavailability_zone_id\tspot_duration_hours\tspot_duration_count\tinterruption_policy\n"
    for p in policies:
        pid = getattr(p, 'id', '')
        flavor_id = getattr(p, 'flavor_id', '')
        sell_mode = getattr(p, 'sell_mode', '')
        sell_status = getattr(p, 'sell_status', '')
        availability_zone_id = getattr(p, 'availability_zone_id', '')
        spot = getattr(p, 'spot_options', None)
        spot_hours = str(getattr(spot, 'longest_spot_duration_hours', '')) if spot else ''
        spot_count = str(getattr(spot, 'largest_spot_duration_count', '')) if spot else ''
        interruption = getattr(spot, 'interruption_policy', '') if spot else ''
        output += f"{pid}\t{flavor_id}\t{sell_mode}\t{sell_status}\t{availability_zone_id}\t{spot_hours}\t{spot_count}\t{interruption}\n"

    # 汇总信息
    showing_count = len(policies)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 规格销售策略，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --flavor_id / --sell_mode / --sell_status 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --flavor_id / --sell_mode / --sell_status 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --flavor_id / --sell_mode / --sell_status 等参数缩小查询范围"
        else:
            output += f"\n可使用 --flavor_id / --sell_mode / --sell_status 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 规格销售策略"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)


    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListFlavorSellPoliciesRequest()
    if args.flavor_id:
        request.flavor_id = args.flavor_id
    if args.sell_mode:
        request.sell_mode = args.sell_mode
    if args.sell_status:
        request.sell_status = args.sell_status
    if args.availability_zone_id:
        request.availability_zone_id = args.availability_zone_id
    if args.longest_spot_duration_hours_gt is not None:
        request.longest_spot_duration_hours_gt = args.longest_spot_duration_hours_gt
    if args.largest_spot_duration_count_gt is not None:
        request.largest_spot_duration_count_gt = args.largest_spot_duration_count_gt
    if args.longest_spot_duration_hours is not None:
        request.longest_spot_duration_hours = args.longest_spot_duration_hours
    if args.largest_spot_duration_count is not None:
        request.largest_spot_duration_count = args.largest_spot_duration_count
    if args.interruption_policy:
        request.interruption_policy = args.interruption_policy

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_policies = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_flavor_sell_policies(request)
            policies = response.sell_policies
            if not policies:
                break
            if marker and all_policies and getattr(policies[0], 'id', None) == getattr(all_policies[-1], 'id', None):
                break
            all_policies.extend(policies)
            if len(policies) < API_LIMIT:
                break
            marker = policies[-1].id
            if not marker:
                break

        if not all_policies:
            print("没有找到 ECS 规格销售策略")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'spot_duration_hours':
                all_policies.sort(key=lambda p: int(getattr(getattr(p, 'spot_options', None), 'longest_spot_duration_hours', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'spot_duration_count':
                all_policies.sort(key=lambda p: int(getattr(getattr(p, 'spot_options', None), 'largest_spot_duration_count', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_policies = all_policies[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_policies, total_count=len(all_policies))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_flavor_sell_policies(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        policies = response.sell_policies

        if not policies:
            print(f"没有找到 ECS 规格销售策略 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            # 无 count 字段时，通过多查的第 FETCH_SIZE 条判断
            has_more = len(policies) > PAGE_SIZE

        if has_more and len(policies) > PAGE_SIZE:
            # 多查的1条存在，说明还有更多，用最后一条展示数据的 id 作为 next_marker
            next_marker = str(policies[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_policies = policies[:PAGE_SIZE]

        # 渲染结果
        render(display_policies, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.flavor_sell_policies 查询失败: {e}")
    exit(1)
