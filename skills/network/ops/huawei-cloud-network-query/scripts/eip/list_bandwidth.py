import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListBandwidthRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限（此 API 上限为 2000）

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询带宽列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--id", type=str, help="带宽唯一标识 ID，精确匹配")
parser.add_argument("--type", type=str, choices=["WHOLE", "PER"], help="带宽类型: WHOLE(共享带宽)/PER(独享带宽)")
parser.add_argument("--bandwidth_type", type=str, choices=["share", "bgp", "telcom", "sbgp"], help="带宽线路类型: share(共享)/bgp(动态BGP)/telcom(联通)/sbgp(静态BGP)")
parser.add_argument("--charge_mode", type=str, choices=["bandwidth", "traffic", "95peak_plus"], help="计费模式: bandwidth(按带宽)/traffic(按流量)/95peak_plus(按增强型95)")
parser.add_argument("--name", type=str, help="带宽名称，精确匹配")
parser.add_argument("--name_like", type=str, help="带宽名称，模糊匹配")
parser.add_argument("--size", type=str, help="带宽大小，单位 Mbit/s，如 10")
parser.add_argument("--ingress_size", type=str, help="入云带宽大小，单位 Mbit/s")
parser.add_argument("--admin_state", type=str, help="带宽状态，如 UP/DOWN")
parser.add_argument("--billing_info", type=str, help="订单信息，用于过滤包周期带宽")
parser.add_argument("--tags", type=str, help="标签，格式: key=value")
parser.add_argument("--enable_bandwidth_rules", type=str, choices=["true", "false"], help="是否启用带宽分组限速: true/false")
parser.add_argument("--rule_quota", type=int, help="带宽分组限速规则数")
parser.add_argument("--public_border_group", type=str, help="站点信息，可通过 list_common_pools.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: size, publicip_count；方向可选: asc(升序), desc(降序)。例如 size:asc 表示按带宽大小升序，publicip_count:desc 表示按关联IP数降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找带宽最小的 5 条带宽，--sort_by size:desc --top 3 查找带宽最大的 3 条带宽")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by size:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('size', 'publicip_count') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: size, publicip_count；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None


# 渲染
def render(bandwidths, total_count=None, has_more=False, next_marker=None):
    if not bandwidths:
        print("没有找到带宽")
        return

    output = f"id\tname\tsize\ttype\tbandwidth_type\tpublicip_count\n"
    for bw in bandwidths:
        bw_id = getattr(bw, 'id', '')
        name = getattr(bw, 'name', '')
        size = str(getattr(bw, 'size', ''))
        bw_type = getattr(bw, 'type', '')
        bandwidth_type = getattr(bw, 'bandwidth_type', '')
        publicip_info = getattr(bw, 'publicip_info', [])
        publicip_count = str(len(publicip_info)) if publicip_info else '0'
        output += f"{bw_id}\t{name}\t{size}\t{bw_type}\t{bandwidth_type}\t{publicip_count}\n"

    # 汇总信息
    showing_count = len(bandwidths)

    if total_count is not None:
        output += f"\n共 {total_count} 条带宽，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --type / --charge_mode 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --type / --charge_mode 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --type / --charge_mode 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --type / --charge_mode 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条带宽"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EipClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EipRegion.value_of(Region)).build()
    if not client:
        print("无法获取 EIP 客户端")
        exit(-1)

    # 构建请求
    request = ListBandwidthRequest()
    if args.id:
        request.id = args.id
    if args.type:
        request.type = args.type
    if args.bandwidth_type:
        request.bandwidth_type = args.bandwidth_type
    if args.charge_mode:
        request.charge_mode = args.charge_mode
    if args.name:
        request.name = args.name
    if args.name_like:
        request.name_like = args.name_like
    if args.size:
        request.size = args.size
    if args.ingress_size:
        request.ingress_size = args.ingress_size
    if args.admin_state:
        request.admin_state = args.admin_state
    if args.billing_info:
        request.billing_info = args.billing_info
    if args.tags:
        request.tags = args.tags
    if args.enable_bandwidth_rules:
        request.enable_bandwidth_rules = args.enable_bandwidth_rules
    if args.rule_quota is not None:
        request.rule_quota = args.rule_quota
    if args.public_border_group:
        request.public_border_group = args.public_border_group

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 排序 + 截取
        all_bandwidths = []
        marker = args.marker or ""
        while True:
            request.limit = str(API_LIMIT)
            if marker:
                request.marker = marker
            response = client.list_bandwidth(request)
            bandwidths = response.eip_bandwidths
            if not bandwidths:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_bandwidths and getattr(bandwidths[0], 'id', None) == getattr(all_bandwidths[-1], 'id', None):
                break
            all_bandwidths.extend(bandwidths)
            if len(bandwidths) < API_LIMIT:
                break
            page_info = getattr(response, 'page_info', None)
            next_marker = getattr(page_info, 'next_marker', None) if page_info else None
            if next_marker:
                marker = next_marker
            else:
                marker = bandwidths[-1].id
                if not marker:
                    break

        if not all_bandwidths:
            print(f"没有找到带宽 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'size':
                all_bandwidths.sort(key=lambda f: int(getattr(f, 'size', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'publicip_count':
                all_bandwidths.sort(key=lambda f: len(getattr(f, 'publicip_info', []) or []), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_bandwidths = all_bandwidths[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_bandwidths, total_count=len(all_bandwidths))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = str(FETCH_SIZE)
        if args.marker:
            request.marker = args.marker

        response = client.list_bandwidth(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        bandwidths = response.eip_bandwidths

        if not bandwidths:
            print(f"没有找到带宽 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        page_info = getattr(response, 'page_info', None)
        next_marker = None
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        elif total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            has_more = len(bandwidths) > PAGE_SIZE

        if has_more and not next_marker and len(bandwidths) > PAGE_SIZE:
            next_marker = str(bandwidths[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_bandwidths = bandwidths[:PAGE_SIZE]

        # 渲染结果
        render(display_bandwidths, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_bandwidth 查询失败: {e}")
    exit(1)
