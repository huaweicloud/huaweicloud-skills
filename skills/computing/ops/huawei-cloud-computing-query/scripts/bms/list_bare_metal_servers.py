import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ListBareMetalServersRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询裸金属服务器列表（OpenStack原生，含总数）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--flavor", type=str, help="裸金属服务器规格ID")
parser.add_argument("--name", type=str, help="裸金属服务器名称")
parser.add_argument("--status", type=str, choices=["ACTIVE", "BUILD", "ERROR", "HARD_REBOOT", "REBOOT", "REBUILD", "SHUTOFF"], help="裸金属服务器状态，只有管理员可以使用DELETED状态过滤查询已经删除的裸金属服务器")
parser.add_argument("--tags", type=str, help="裸金属服务器标签：__type_baremetal")
parser.add_argument("--reservation_id", type=str, help="批量创建裸金属服务器时，指定返回的ID，用于查询本次批量创建的裸金属服务器")
parser.add_argument("--detail", type=str, choices=["1", "2", "3", "4"], help="查询裸金属服务器结果的详细级别，级别越高，查询到的裸金属服务器信息越多，默认为4")
parser.add_argument("--enterprise_project_id", type=str, help="查询绑定某个企业项目的裸金属服务器，查询所有可传 all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: vcpus, ram, disk, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。例如 size:asc 表示按综合规格升序，vcpus:desc 表示按 vCPU 降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个裸金属服务器")
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
    if len(sort_parts) != 2 or sort_parts[0] not in ('vcpus', 'ram', 'disk', 'size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: vcpus, ram, disk, size；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None


# 渲染
def render(servers, total_count=None, has_more=False, next_marker=None):
    if not servers:
        print("没有找到裸金属服务器")
        return

    output = f"id\tname\tstatus\tflavor_id\tvcpus\tmemory(MiB)\tdisk(GB)\tavailability_zone\tcreated\n"
    for server in servers:
        sid = getattr(server, 'id', '')
        name = getattr(server, 'name', '')
        status = getattr(server, 'status', '')
        flavor = getattr(server, 'flavor', None)
        flavor_id = getattr(flavor, 'id', '') if flavor else ''
        vcpus = getattr(flavor, 'vcpus', '') if flavor else ''
        ram = getattr(flavor, 'ram', '') if flavor else ''
        disk = getattr(flavor, 'disk', '') if flavor else ''
        availability_zone = getattr(server, 'os_ext_a_zavailability_zone', '')
        created = getattr(server, 'created', '')
        output += f"{sid}\t{name}\t{status}\t{flavor_id}\t{vcpus}\t{ram}\t{disk}\t{availability_zone}\t{created}\n"

    # 汇总信息
    showing_count = len(servers)

    if total_count is not None:
        output += f"\n共 {total_count} 条裸金属服务器，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --flavor 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --status / --flavor 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --flavor 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --status / --flavor 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条裸金属服务器"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ListBareMetalServersRequest()
    if args.flavor:
        request.flavor = args.flavor
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.tags:
        request.tags = args.tags
    if args.reservation_id:
        request.reservation_id = args.reservation_id
    if args.detail:
        request.detail = args.detail
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地过滤
        all_servers = []
        current_page = 1
        while True:
            request.limit = API_LIMIT
            request.offset = current_page
            response = client.list_bare_metal_servers(request)
            servers = response.servers
            if not servers:
                break
            all_servers.extend(servers)
            if len(servers) < API_LIMIT:
                break
            current_page += 1

        if not all_servers:
            print("没有找到裸金属服务器")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'vcpus':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'ram':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'disk':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'disk', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'size':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0) * (int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0) // 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_servers = all_servers[:args.top]

        # 渲染过滤结果（全量已拉取，无需翻页）
        render(all_servers, total_count=len(all_servers))
    else:
        # 无自定义过滤参数：只查1次
        # 计算 offset（API 的 offset 是页码，从1开始；marker 存储的是页码值）
        current_page = int(args.marker) if args.marker else 1

        request.limit = FETCH_SIZE
        request.offset = current_page  # API offset 是页码，从1开始

        # 只做一次查询
        response = client.list_bare_metal_servers(request)
        total_count = getattr(response, 'count', None)
        servers = response.servers

        if not servers:
            print(f"没有找到裸金属服务器 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = (current_page * PAGE_SIZE) < total_count
        else:
            has_more = len(servers) > PAGE_SIZE

        if has_more:
            next_marker = str(current_page + 1)

        # 只展示前 PAGE_SIZE 条
        display_servers = servers[:PAGE_SIZE]

        # 渲染结果
        render(display_servers, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"bms.list_bare_metal_servers 查询失败: {e}")
    exit(1)
