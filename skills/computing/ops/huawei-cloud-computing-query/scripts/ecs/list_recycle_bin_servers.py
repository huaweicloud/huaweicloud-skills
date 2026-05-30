import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListRecycleBinServersRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 回收站服务器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="服务器名称，支持模糊匹配")
parser.add_argument("--all_tenants", type=str, choices=["0", "1"], help="管理员字段：1-返回所有租户的 VM，0-返回当前租户的 VM")
parser.add_argument("--availability_zone", type=str, help="可用区，可通过 list_server_az_info.py 获取")
parser.add_argument("--ip_address", type=str, help="按 IP 地址过滤")
parser.add_argument("--tags", type=str, nargs="+", help="按标签过滤，格式为 key=value，可指定多个")
parser.add_argument("--tags_key", type=str, nargs="+", help="按标签 key 过滤，可指定多个")
parser.add_argument("--expect_fields", type=str, help="控制查询输出的额外字段")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(servers, total_count=None, has_more=False, next_marker=None):
    if not servers:
        print("没有找到 ECS 回收站服务器")
        return

    output = f"id\tname\tstatus\tflavor_id\tavailability_zone\tcreated\n"
    for server in servers:
        sid = getattr(server, 'id', '')
        name = getattr(server, 'name', '')
        status = getattr(server, 'status', '')
        flavor = getattr(server, 'flavor', None)
        flavor_id = getattr(flavor, 'id', '') if flavor else ''
        availability_zone = getattr(server, 'os_ext_a_zavailability_zone', '')
        created = getattr(server, 'created', '')
        output += f"{sid}\t{name}\t{status}\t{flavor_id}\t{availability_zone}\t{created}\n"

    # 汇总信息
    showing_count = len(servers)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 回收站服务器，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --availability_zone / --ip_address 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --availability_zone / --ip_address 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --availability_zone / --ip_address 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --availability_zone / --ip_address 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 回收站服务器"

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
    request = ListRecycleBinServersRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.name:
        request.name = args.name
    if args.all_tenants:
        request.all_tenants = args.all_tenants
    if args.availability_zone:
        request.availability_zone = args.availability_zone
    if args.ip_address:
        request.ip_address = args.ip_address
    if args.tags:
        request.tags = args.tags
    if args.tags_key:
        request.tags_key = args.tags_key
    if args.expect_fields:
        request.expect_fields = args.expect_fields

    # 只做一次查询
    response = client.list_recycle_bin_servers(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    servers = response.servers

    if not servers:
        print(f"没有找到 ECS 回收站服务器 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > PAGE_SIZE
    else:
        # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(servers) > PAGE_SIZE

    if has_more and len(servers) > PAGE_SIZE:
        # 多查的1条存在，说明还有更多，用最后一条展示数据的 id 作为 next_marker
        next_marker = str(servers[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_servers = servers[:PAGE_SIZE]

    # 渲染结果
    render(display_servers, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.recycle_bin_servers 查询失败: {e}")
    exit(1)
