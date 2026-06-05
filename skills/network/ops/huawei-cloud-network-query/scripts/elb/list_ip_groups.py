import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListIpGroupsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB IP 地址组列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: ip_count；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by ip_count:desc --top 5 查找 IP 数量最多的 5 个地址组")
parser.add_argument("--id", type=str, nargs="+", help="IP地址组ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="IP地址组名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="IP地址组描述，支持多值查询")
parser.add_argument("--ip_list", type=str, nargs="+", help="IP地址组包含的IP地址，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by ip_count:desc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('ip_count',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: ip_count；方向可选: asc, desc。例如 ip_count:desc")
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

    request = ListIpGroupsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.ip_list:
        request.ip_list = args.ip_list
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_ipgroups = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_ip_groups(request)
            ipgroups = response.ipgroups
            if not ipgroups:
                break
            if marker and all_ipgroups and getattr(ipgroups[0], 'id', None) == getattr(all_ipgroups[-1], 'id', None):
                break
            all_ipgroups.extend(ipgroups)
            if len(ipgroups) < API_LIMIT:
                break
            marker = ipgroups[-1].id
            if not marker:
                break

        if not all_ipgroups:
            print("没有找到 IP 地址组")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'ip_count':
                all_ipgroups.sort(key=lambda f: len(getattr(f, 'ip_list', []) or []), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_ipgroups = all_ipgroups[:args.top]

        # 渲染
        output = f"id\tname\tdescription\tproject_id\tip_count\tcreated_at\n"
        for item in all_ipgroups:
            id = getattr(item, 'id', '')
            name = getattr(item, 'name', '')
            description = getattr(item, 'description', '')
            project_id = getattr(item, 'project_id', '')
            ip_list = getattr(item, 'ip_list', [])
            ip_count = len(ip_list) if ip_list else 0
            created_at = getattr(item, 'created_at', '')
            output += f"{id}\t{name}\t{description}\t{project_id}\t{ip_count}\t{created_at}\n"
        output += f"\n共 {len(all_ipgroups)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_ip_groups(request)
        ipgroups = response.ipgroups

        if not ipgroups:
            print(f"没有找到 IP 地址组 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(ipgroups) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(ipgroups[PAGE_SIZE - 1], 'id', ''))

        display_ipgroups = ipgroups[:PAGE_SIZE]

        output = f"id\tname\tdescription\tproject_id\tip_count\tcreated_at\n"
        for item in display_ipgroups:
            id = getattr(item, 'id', '')
            name = getattr(item, 'name', '')
            description = getattr(item, 'description', '')
            project_id = getattr(item, 'project_id', '')
            ip_list = getattr(item, 'ip_list', [])
            ip_count = len(ip_list) if ip_list else 0
            created_at = getattr(item, 'created_at', '')
            output += f"{id}\t{name}\t{description}\t{project_id}\t{ip_count}\t{created_at}\n"

        if has_more:
            output += f"\n当前返回 {len(display_ipgroups)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_ipgroups)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_ip_groups 查询失败: {e}")
    exit(1)
