import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListResizeFlavorsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 变更规格列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--instance_uuid", type=str, help="云服务器 ID（UUID），可通过 list_servers_details.py 获取。instance_uuid、source_flavor_id、source_flavor_name 不能都为空")
parser.add_argument("--source_flavor_id", type=str, help="源规格 ID，可通过 list_flavors.py 获取")
parser.add_argument("--source_flavor_name", type=str, help="源规格名称")
parser.add_argument("--sort_key", type=str, choices=["flavorid", "name", "memory_mb", "vcpus", "root_gb"], help="排序字段，默认 flavorid")
parser.add_argument("--sort_dir", type=str, choices=["asc", "desc"], help="排序方向，默认 asc")
parser.add_argument("--sort_by", type=str, help="客户端排序字段和方向，格式: 字段:方向。字段可选: vcpus, ram, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。与 --top 配合使用可快速查找最值。注意：此参数为客户端排序，与 --sort_key/--sort_dir（服务端排序）不同")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个变更规格")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by vcpus:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('vcpus', 'ram', 'size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: vcpus, ram, size；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（排序需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(flavors, total_count=None, has_more=False, next_marker=None):
    if not flavors:
        print("没有找到 ECS 变更规格")
        return

    output = f"flavor_id\tname\tvcpus\tram(GiB)\n"
    for f in flavors:
        flavor_id = getattr(f, 'id', '')
        name = getattr(f, 'name', '')
        vcpus = str(getattr(f, 'vcpus', ''))
        ram = str(int(getattr(f, 'ram', 0)) // 1024)
        output += f"{flavor_id}\t{name}\t{vcpus}\t{ram}\n"

    # 汇总信息
    showing_count = len(flavors)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 变更规格，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --instance_uuid / --source_flavor_id / --source_flavor_name 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --instance_uuid / --source_flavor_id / --source_flavor_name 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --instance_uuid / --source_flavor_id / --source_flavor_name 等参数缩小查询范围"
        else:
            output += f"\n可使用 --instance_uuid / --source_flavor_id / --source_flavor_name 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 变更规格"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListResizeFlavorsRequest()
    if args.instance_uuid:
        request.instance_uuid = args.instance_uuid
    if args.source_flavor_id:
        request.source_flavor_id = args.source_flavor_id
    if args.source_flavor_name:
        request.source_flavor_name = args.source_flavor_name
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_flavors = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_resize_flavors(request)
            flavors = response.flavors
            if not flavors:
                break
            if marker and all_flavors and getattr(flavors[0], 'id', None) == getattr(all_flavors[-1], 'id', None):
                break
            all_flavors.extend(flavors)
            if len(flavors) < API_LIMIT:
                break
            marker = flavors[-1].id
            if not marker:
                break

        if not all_flavors:
            print("没有找到 ECS 变更规格")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'vcpus':
                all_flavors.sort(key=lambda f: int(getattr(f, 'vcpus', 0)), reverse=(sort_dir == 'desc'))
            elif sort_field == 'ram':
                all_flavors.sort(key=lambda f: int(getattr(f, 'ram', 0)), reverse=(sort_dir == 'desc'))
            elif sort_field == 'size':
                all_flavors.sort(key=lambda f: int(getattr(f, 'vcpus', 0)) * (int(getattr(f, 'ram', 0)) // 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_flavors = all_flavors[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_flavors, total_count=len(all_flavors))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_resize_flavors(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        flavors = response.flavors

        if not flavors:
            print(f"没有找到 ECS 变更规格 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
            has_more = len(flavors) > PAGE_SIZE

        if has_more and len(flavors) > PAGE_SIZE:
            # 多查的1条存在，说明还有更多，用最后一条展示数据的 id 作为 next_marker
            next_marker = str(flavors[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_flavors = flavors[:PAGE_SIZE]

        # 渲染结果
        render(display_flavors, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.resize_flavors 查询失败: {e}")
    exit(1)
