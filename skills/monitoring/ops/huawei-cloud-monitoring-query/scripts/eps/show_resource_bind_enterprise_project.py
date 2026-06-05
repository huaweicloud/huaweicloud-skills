import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowResourceBindEnterpriseProjectRequest, ResqEpResouce, Match
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目绑定的资源列表")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--enterprise_project_id", type=str, required=True, help="企业项目ID，可通过 list_enterprise_projects.py 获取")
parser.add_argument("--resource_types", type=str, required=True, nargs="+", help="资源类型列表，如 ecs vpc eip disk 等，可通过 list_providers.py 查询支持的类型")
parser.add_argument("--projects", type=str, nargs="+", help="项目ID列表，resource_types中包含region级别服务时为必选")
parser.add_argument("--match", type=str, action="append", help="搜索字段，格式: resource_name=xxx，可多次指定")
parser.add_argument("--offset", type=int, help="索引位置，从offset指定的下一条数据开始查询，不能为负数，默认0")
parser.add_argument("--limit", type=int, help="查询记录数，默认1000，最大1000，最小1")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(resources, errors, total_count):
    if not resources and not errors:
        print(f"没有找到绑定的资源")
        return

    if resources:
        output = f"resource_id\tresource_name\tresource_type\tproject_id\tproject_name\n"
        for r in resources:
            resource_id = getattr(r, 'resource_id', '')
            resource_name = getattr(r, 'resource_name', '')
            resource_type = getattr(r, 'resource_type', '')
            project_id = getattr(r, 'project_id', '')
            project_name = getattr(r, 'project_name', '')
            output += f"{resource_id}\t{resource_name}\t{resource_type}\t{project_id}\t{project_name}\n"
        output += f"\n共 {total_count} 个资源"
    else:
        output = ""

    if errors:
        output += f"\n\nerrors:\n"
        for e in errors:
            e_code = getattr(e, 'code', '')
            e_msg = getattr(e, 'message', '')
            output += f"  {e_code}\t{e_msg}\n"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    request = ShowResourceBindEnterpriseProjectRequest()
    request.enterprise_project_id = args.enterprise_project_id

    body = ResqEpResouce()
    body.resource_types = args.resource_types
    if args.projects:
        body.projects = args.projects
    if args.offset is not None:
        body.offset = args.offset
    if args.limit is not None:
        body.limit = args.limit

    # 解析 match
    if args.match:
        matches_list = []
        for item in args.match:
            if '=' not in item:
                print(f"match格式错误: '{item}'，应为 key=value 格式，key固定为resource_name")
                exit(1)
            k, v = item.split('=', 1)
            matches_list.append(Match(key=k, value=v))
        body.matches = matches_list

    request.body = body
    response = client.show_resource_bind_enterprise_project(request)

    resources = getattr(response, 'resources', []) or []
    errors = getattr(response, 'errors', []) or []
    total_count = getattr(response, 'total_count', 0)

    if not resources and not errors:
        print(f"没有找到企业项目绑定的资源 (企业项目ID: {args.enterprise_project_id})")
        exit(0)

    render(resources, errors, total_count)
except Exception as e:
    print(f"eps.show_resource_bind_enterprise_project 查询失败: {e}")
    exit(1)
