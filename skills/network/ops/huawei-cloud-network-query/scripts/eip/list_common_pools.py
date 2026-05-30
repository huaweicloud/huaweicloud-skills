import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListCommonPoolsRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限（此 API 上限为 2000）

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公共池列表（可用弹性公网IP池）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--name", type=str, help="公共池名称，精确匹配")
parser.add_argument("--public_border_group", type=str, help="站点信息（中心/边缘），可通过 list_common_pools.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: used；方向可选: asc(升序), desc(降序)。例如 used:asc 表示按已使用数量升序，used:desc 表示按已使用数量降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by used:asc --top 5 查找使用量最小的 5 个公共池，--sort_by used:desc --top 3 查找使用量最大的 3 个公共池")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by used:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('used',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: used；方向可选: asc, desc。例如 used:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None


# 渲染
def render(pools, total_count=None, has_more=False, next_marker=None):
    if not pools:
        print("没有找到公共池")
        return

    output = f"name\ttype\tstatus\tused\tpublic_border_group\tallow_share_bandwidth_types\n"
    for pool in pools:
        name = getattr(pool, 'name', '')
        pool_type = getattr(pool, 'type', '')
        status = getattr(pool, 'status', '')
        used = str(getattr(pool, 'used', ''))
        public_border_group = getattr(pool, 'public_border_group', '')
        allow_types = getattr(pool, 'allow_share_bandwidth_types', [])
        allow_types_str = ','.join(allow_types) if allow_types else ''
        output += f"{name}\t{pool_type}\t{status}\t{used}\t{public_border_group}\t{allow_types_str}\n"

    # 汇总信息
    showing_count = len(pools)

    if total_count is not None:
        output += f"\n共 {total_count} 个公共池，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --public_border_group 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --public_border_group 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --public_border_group 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --public_border_group 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个公共池"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EipClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EipRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EIP 客户端")
        exit(-1)

    # 构建请求
    # API 仅支持 offset 分页（无 marker），用 offset 模拟 marker 翻页
    request = ListCommonPoolsRequest()
    if args.name:
        request.name = args.name
    if args.public_border_group:
        request.public_border_group = args.public_border_group

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 排序 + 截取
        all_pools = []
        offset = int(args.marker) if args.marker else 0
        while True:
            request.limit = API_LIMIT
            request.offset = offset
            response = client.list_common_pools(request)
            pools = response.common_pools
            if not pools:
                break
            all_pools.extend(pools)
            if len(pools) < API_LIMIT:
                break
            offset += API_LIMIT

        if not all_pools:
            print(f"没有找到公共池 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'used':
                all_pools.sort(key=lambda f: int(getattr(f, 'used', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_pools = all_pools[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_pools, total_count=len(all_pools))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.offset = int(args.marker)

        response = client.list_common_pools(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        pools = response.common_pools

        if not pools:
            print(f"没有找到公共池 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
            has_more = len(pools) > PAGE_SIZE

        if has_more and len(pools) > PAGE_SIZE:
            # API 仅支持 offset 分页，next_marker 为下一页的 offset 值
            current_offset = int(args.marker) if args.marker else 0
            next_marker = str(current_offset + PAGE_SIZE)

        # 只展示前 PAGE_SIZE 条
        display_pools = pools[:PAGE_SIZE]

        # 渲染结果
        render(display_pools, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_common_pools 查询失败: {e}")
    exit(1)
