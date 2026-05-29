import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListMembersRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB 后端服务器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--pool_id", type=str, required=True, help="后端服务器组 ID，可通过 list_pools.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: protocol_port, weight；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by weight:asc --top 5 查找权重最小的 5 个后端服务器")
parser.add_argument("--id", type=str, nargs="+", help="后端服务器ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="后端服务器名称，支持多值查询")
parser.add_argument("--address", type=str, nargs="+", help="后端服务器对应的IP地址，支持多值查询")
parser.add_argument("--protocol_port", type=int, nargs="+", help="后端服务器业务端口号，支持多值查询")
parser.add_argument("--weight", type=int, nargs="+", help="后端服务器的权重，取值0-100，支持多值查询")
parser.add_argument("--admin_state_up", type=bool, help="后端服务器的管理状态，true启用，false停用")
parser.add_argument("--operating_status", type=str, nargs="+", help="后端服务器的健康状态，支持多值查询，取值: NO_MONITOR INITIAL ONLINE OFFLINE UNKNOWN")
parser.add_argument("--subnet_cidr_id", type=str, nargs="+", help="后端服务器所在子网的ID，支持多值查询")
parser.add_argument("--ip_version", type=str, nargs="+", help="后端服务器的IP地址版本，支持多值查询，取值: v4 v6")
parser.add_argument("--member_type", type=str, nargs="+", help="后端服务器的类型，支持多值查询，取值: ip instance")
parser.add_argument("--instance_id", type=str, nargs="+", help="member关联的ECS实例ID，支持多值查询")
parser.add_argument("--availability_zone", type=str, nargs="+", help="后端服务器的可用区，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by weight:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('protocol_port', 'weight') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: protocol_port, weight；方向可选: asc, desc。例如 weight:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListMembersRequest()
    request.pool_id = args.pool_id
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.address:
        request.address = args.address
    if args.protocol_port is not None:
        request.protocol_port = args.protocol_port
    if args.weight is not None:
        request.weight = args.weight
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.operating_status:
        request.operating_status = args.operating_status
    if args.subnet_cidr_id:
        request.subnet_cidr_id = args.subnet_cidr_id
    if args.ip_version:
        request.ip_version = args.ip_version
    if args.member_type:
        request.member_type = args.member_type
    if args.instance_id:
        request.instance_id = args.instance_id
    if args.availability_zone:
        request.availability_zone = args.availability_zone
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_members = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_members(request)
            members = response.members
            if not members:
                break
            if marker and all_members and getattr(members[0], 'id', None) == getattr(all_members[-1], 'id', None):
                break
            all_members.extend(members)
            if len(members) < API_LIMIT:
                break
            marker = members[-1].id
            if not marker:
                break

        if not all_members:
            print("没有找到后端服务器")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'protocol_port':
                all_members.sort(key=lambda f: int(getattr(f, 'protocol_port', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'weight':
                all_members.sort(key=lambda f: int(getattr(f, 'weight', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_members = all_members[:args.top]

        # 渲染
        output = f"name\tid\taddress\tprotocol_port\tweight\toperating_status\tadmin_state_up\tmember_type\tinstance_id\n"
        for item in all_members:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            address = getattr(item, 'address', '')
            protocol_port = getattr(item, 'protocol_port', '')
            weight = getattr(item, 'weight', '')
            operating_status = getattr(item, 'operating_status', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            member_type = getattr(item, 'member_type', '')
            instance_id = getattr(item, 'instance_id', '')
            output += f"{name}\t{id}\t{address}\t{protocol_port}\t{weight}\t{operating_status}\t{admin_state_up}\t{member_type}\t{instance_id}\n"
        output += f"\n共 {len(all_members)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_members(request)
        members = response.members

        if not members:
            print(f"没有找到后端服务器 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(members) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(members[PAGE_SIZE - 1], 'id', ''))

        display_members = members[:PAGE_SIZE]

        output = f"name\tid\taddress\tprotocol_port\tweight\toperating_status\tadmin_state_up\tmember_type\tinstance_id\n"
        for item in display_members:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            address = getattr(item, 'address', '')
            protocol_port = getattr(item, 'protocol_port', '')
            weight = getattr(item, 'weight', '')
            operating_status = getattr(item, 'operating_status', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            member_type = getattr(item, 'member_type', '')
            instance_id = getattr(item, 'instance_id', '')
            output += f"{name}\t{id}\t{address}\t{protocol_port}\t{weight}\t{operating_status}\t{admin_state_up}\t{member_type}\t{instance_id}\n"

        if has_more:
            output += f"\n当前返回 {len(display_members)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_members)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_members 查询失败: {e}")
    exit(1)
