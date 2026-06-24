import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient, ListServersDetailsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="按 ID 查询 ECS 实例详情")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--instance_id", type=str, required=True, help="实例 ID（UUID），可逗号分隔多个，可通过 list_servers_details.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: vcpus, ram, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个 ECS")
args = parser.parse_args()

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
def render(servers, total_count=None, has_more=False, next_marker=None):
    if not servers:
        print("没有找到 ECS")
        return

    output = f"id\tname\tstatus\tflavor_id\tvcpus\tmemory(GiB)\tavailability_zone\tcreated\n"
    for server in servers:
        sid = getattr(server, 'id', '')
        name = getattr(server, 'name', '')
        status = getattr(server, 'status', '')
        flavor = getattr(server, 'flavor', None)
        flavor_id = getattr(flavor, 'id', '') if flavor else ''
        vcpus = getattr(flavor, 'vcpus', '') if flavor else ''
        ram_mb = getattr(flavor, 'ram', 0) if flavor else 0
        ram_gib = str(int(ram_mb) // 1024) if ram_mb else ''
        availability_zone = getattr(server, 'os_ext_a_zavailability_zone', '')
        created = getattr(server, 'created', '')
        output += f"{sid}\t{name}\t{status}\t{flavor_id}\t{vcpus}\t{ram_gib}\t{availability_zone}\t{created}\n"

    # 汇总信息
    showing_count = len(servers)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 条 ECS"

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

    # 构建请求，server_id 支持逗号分隔多个 ID，结果可能不止1条
    request = ListServersDetailsRequest()
    request.server_id = args.instance_id

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_servers = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_servers_details(request)
            servers = response.servers
            if not servers:
                break
            if marker and all_servers and getattr(servers[0], 'id', None) == getattr(all_servers[-1], 'id', None):
                break
            all_servers.extend(servers)
            if len(servers) < API_LIMIT:
                break
            marker = servers[-1].id
            if not marker:
                break

        if not all_servers:
            print("没有找到 ECS")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'vcpus':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'ram':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'size':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0) * (int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0) // 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_servers = all_servers[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_servers, total_count=len(all_servers))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE

        response = client.list_servers_details(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        servers = response.servers

        if not servers:
            print(f"没有找到 ECS (区域: {Region}), server_id: {args.instance_id}")
            exit(0)

        # 判断是否还有更多数据
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            has_more = len(servers) > PAGE_SIZE

        if has_more and len(servers) > PAGE_SIZE:
            next_marker = str(servers[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_servers = servers[:PAGE_SIZE]

        # 渲染结果
        render(display_servers, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.detail 查询失败: {e}")
    exit(1)
