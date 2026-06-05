import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListCloudServersRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 云服务器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, help="云服务器 ID（UUID），精确匹配")
parser.add_argument("--name", type=str, help="云服务器名称，支持模糊匹配")
parser.add_argument("--status", type=str, choices=["ACTIVE", "BUILD", "ERROR", "HARD_REBOOT", "MIGRATING", "REBOOT", "RESIZE", "REVERT_RESIZE", "SHELVED", "SHELVED_OFFLOADED", "SHUTOFF", "UNKNOWN", "VERIFY_RESIZE"], help="云服务器状态")
parser.add_argument("--in_recycle_bin", type=str, choices=["true", "false"], help="是否在回收站中，true/false")
parser.add_argument("--spod_id", type=str, help="共池裸机按整机柜发放的同一批次的批创 ID")
parser.add_argument("--flavor_name", type=str, help="云服务器规格名称")
parser.add_argument("--image_id", type=str, help="镜像 ID")
parser.add_argument("--metadata", type=str, help="元数据过滤，格式 key=value")
parser.add_argument("--metadata_key", type=str, help="元数据 key 过滤")
parser.add_argument("--tags", type=str, help="查询 tag 字段中包含该值的云服务器")
parser.add_argument("--not_tags", type=str, help="查询 tag 字段中不包含该值的云服务器")
parser.add_argument("--availability_zone", type=str, help="可用区，模糊匹配")
parser.add_argument("--availability_zone_eq", type=str, help="可用区，精确匹配")
parser.add_argument("--charging_mode", type=str, choices=["0", "1", "2"], help="计费类型：0-按需，1-包周期，2-竞价")
parser.add_argument("--key_name", type=str, help="云服务器使用的密钥对名称")
parser.add_argument("--launched_since", type=str, help="过滤在此时间之后启动的云服务器，ISO8601 格式，如 2023-01-01T00:00:00Z")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID，查询所有可传 all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--expect_fields", type=str, nargs="+", choices=["launched_at", "key_name", "locked", "root_device_name", "tenancy", "dedicated_host_id", "enterprise_project_id", "tags", "metadata", "addresses", "security_groups", "volumes_attached", "image", "power_state", "cpu_options", "market_info"], help="额外返回的字段，默认不展示的字段需通过此参数指定才返回，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: vcpus, ram, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。例如 size:asc 表示按综合规格升序，vcpus:asc 表示按 vCPU 升序，ram:desc 表示按内存降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个云服务器，--sort_by size:desc --top 3 查找综合规格最大的 3 个云服务器")
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
def render(servers, show_image, total_count=None, has_more=False, next_marker=None):
    if not servers:
        print("没有找到 ECS 云服务器")
        return

    header = "id\tname\tstatus\tflavor_id\tvcpus\tram(GiB)\tavailability_zone\tcreated"
    if show_image:
        header += "\timage_id"
    output = header + "\n"
    for server in servers:
        sid = getattr(server, 'id', '')
        name = getattr(server, 'name', '')
        status = getattr(server, 'status', '')
        flavor = getattr(server, 'flavor', None)
        flavor_id = getattr(flavor, 'id', '') if flavor else ''
        vcpus = str(getattr(flavor, 'vcpus', '')) if flavor else ''
        ram = str(int(getattr(flavor, 'ram', 0)) // 1024) if flavor else ''
        availability_zone = getattr(server, 'availability_zone', '')
        created = getattr(server, 'created', '')
        row = f"{sid}\t{name}\t{status}\t{flavor_id}\t{vcpus}\t{ram}\t{availability_zone}\t{created}"
        if show_image:
            image = getattr(server, 'image', None)
            image_id = getattr(image, 'id', '') if image else ''
            row += f"\t{image_id}"
        output += row + "\n"

    # 汇总信息
    showing_count = len(servers)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 云服务器，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --charging_mode 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --status / --charging_mode 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --charging_mode 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --status / --charging_mode 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 云服务器"

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
    request = ListCloudServersRequest()
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.in_recycle_bin:
        request.in_recycle_bin = args.in_recycle_bin == "true"
    if args.spod_id:
        request.spod_id = args.spod_id
    if args.flavor_name:
        request.flavor_name = args.flavor_name
    if args.image_id:
        request.image_id = args.image_id
    if args.metadata:
        request.metadata = args.metadata
    if args.metadata_key:
        request.metadata_key = args.metadata_key
    if args.tags:
        request.tags = args.tags
    if args.not_tags:
        request.not_tags = args.not_tags
    if args.availability_zone:
        request.availability_zone = args.availability_zone
    if args.availability_zone_eq:
        request.availability_zone_eq = args.availability_zone_eq
    if args.charging_mode:
        request.charging_mode = args.charging_mode
    if args.key_name:
        request.key_name = args.key_name
    if args.launched_since:
        request.launched_since = args.launched_since
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.expect_fields:
        request.expect_fields = args.expect_fields

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_servers = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_cloud_servers(request)
            servers = response.servers
            if not servers:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_servers and getattr(servers[0], 'id', None) == getattr(all_servers[-1], 'id', None):
                break
            all_servers.extend(servers)
            if len(servers) < API_LIMIT:
                break
            marker = servers[-1].id
            if not marker:
                break

        if not all_servers:
            print("没有找到 ECS 云服务器")
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
        show_image = args.expect_fields and "image" in args.expect_fields
        render(all_servers, show_image, total_count=len(all_servers))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_cloud_servers(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        servers = response.servers

        if not servers:
            print(f"没有找到 ECS 云服务器 (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            # 无 count 字段时，通过多查的第 FETCH_SIZE 条判断
            has_more = len(servers) > PAGE_SIZE

        if has_more and len(servers) > PAGE_SIZE:
            # 多查的1条存在，说明还有更多，用最后一条展示数据的 id 作为 next_marker
            next_marker = str(servers[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_servers = servers[:PAGE_SIZE]

        # 渲染结果
        show_image = args.expect_fields and "image" in args.expect_fields
        render(display_servers, show_image, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.cloud_servers 查询失败: {e}")
    exit(1)
