import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListBandwidthsLimitRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限（此 API 上限为 2000）

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询租户带宽限制（带宽大小范围）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--charge_mode", type=str, choices=["bandwidth", "traffic", "95peak_plus"], help="计费模式: bandwidth(按带宽)/traffic(按流量)/95peak_plus(按增强型95)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: min_size, max_size；方向可选: asc(升序), desc(降序)。例如 min_size:asc 表示按最小带宽升序，max_size:desc 表示按最大带宽降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by min_size:asc --top 5 查找最小带宽下限最小的 5 条限制，--sort_by max_size:desc --top 3 查找最大带宽上限最大的 3 条限制")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by min_size:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('min_size', 'max_size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: min_size, max_size；方向可选: asc, desc。例如 min_size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None


# 渲染
def render(limits, total_count=None, has_more=False, next_marker=None):
    if not limits:
        print("没有找到带宽限制")
        return

    output = f"id\tcharge_mode\tmin_size\tmax_size\n"
    for item in limits:
        item_id = getattr(item, 'id', '')
        charge_mode = getattr(item, 'charge_mode', '')
        min_size = str(getattr(item, 'min_size', ''))
        max_size = str(getattr(item, 'max_size', ''))
        output += f"{item_id}\t{charge_mode}\t{min_size}\t{max_size}\n"

    # 汇总信息
    showing_count = len(limits)

    if total_count is not None:
        output += f"\n共 {total_count} 条带宽限制，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 条带宽限制"

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
    request = ListBandwidthsLimitRequest()
    if args.charge_mode:
        request.charge_mode = args.charge_mode

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 排序 + 截取
        all_limits = []
        marker = args.marker or ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_bandwidths_limit(request)
            limits = response.eip_bandwidth_limits
            if not limits:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_limits and getattr(limits[0], 'id', None) == getattr(all_limits[-1], 'id', None):
                break
            all_limits.extend(limits)
            if len(limits) < API_LIMIT:
                break
            page_info = getattr(response, 'page_info', None)
            next_marker = getattr(page_info, 'next_marker', None) if page_info else None
            if next_marker:
                marker = next_marker
            else:
                marker = limits[-1].id
                if not marker:
                    break

        if not all_limits:
            print(f"没有找到带宽限制 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'min_size':
                all_limits.sort(key=lambda f: int(getattr(f, 'min_size', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'max_size':
                all_limits.sort(key=lambda f: int(getattr(f, 'max_size', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_limits = all_limits[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_limits, total_count=len(all_limits))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_bandwidths_limit(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        limits = response.eip_bandwidth_limits

        if not limits:
            print(f"没有找到带宽限制 (区域: {Region})")
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
            has_more = len(limits) > PAGE_SIZE

        if has_more and not next_marker and len(limits) > PAGE_SIZE:
            next_marker = str(limits[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_limits = limits[:PAGE_SIZE]

        # 渲染结果
        render(display_limits, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_bandwidths_limit 查询失败: {e}")
    exit(1)
