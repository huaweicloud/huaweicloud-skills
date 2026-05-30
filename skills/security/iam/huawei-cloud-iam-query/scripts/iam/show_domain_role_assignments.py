import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainRoleAssignmentsRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询域角色分配 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, help="域 ID")
parser.add_argument("--role_id", type=str, help="角色 ID")
parser.add_argument("--subject", type=str, help="主体类型")
parser.add_argument("--page", type=int, help="分页页码")
parser.add_argument("--per_page", type=int, help="每页数量")
parser.add_argument("--subject_user_id", type=str, help="主体用户 ID")
parser.add_argument("--subject_group_id", type=str, help="主体用户组 ID")
parser.add_argument("--subject_agency_id", type=str, help="主体委托 ID")
parser.add_argument("--scope", type=str, choices=["domain", "project", "enterprise_project", "all"], help="授权范围，domain: 域，project: 项目，enterprise_project: 企业项目，all: 全部")
parser.add_argument("--scope_project_id", type=str, help="范围项目 ID")
parser.add_argument("--scope_domain_id", type=str, help="范围域 ID")
parser.add_argument("--scope_enterprise_projects_id", type=str, help="范围企业项目ID，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--is_inherited", type=bool, help="是否包含继承的授权")
parser.add_argument("--include_group", type=bool, help="是否包含用户组授权")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = ShowDomainRoleAssignmentsRequest()
    if args.domain_id:
        request.domain_id = args.domain_id
    if args.role_id:
        request.role_id = args.role_id
    if args.subject:
        request.subject = args.subject
    if args.page is not None:
        request.page = args.page
    if args.per_page is not None:
        request.per_page = args.per_page
    if args.subject_user_id:
        request.subject_user_id = args.subject_user_id
    if args.subject_group_id:
        request.subject_group_id = args.subject_group_id
    if args.subject_agency_id:
        request.subject_agency_id = args.subject_agency_id
    if args.scope:
        request.scope = args.scope
    if args.scope_project_id:
        request.scope_project_id = args.scope_project_id
    if args.scope_domain_id:
        request.scope_domain_id = args.scope_domain_id
    if args.scope_enterprise_projects_id:
        request.scope_enterprise_projects_id = args.scope_enterprise_projects_id
    if args.is_inherited is not None:
        request.is_inherited = args.is_inherited
    if args.include_group is not None:
        request.include_group = args.include_group
    response = client.show_domain_role_assignments(request)
    items = response.role_assignments
    if not items:
        print(f"没有找到数据 (区域: {Region})")
        exit(0)

    output = f"id	name\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        output += f"{id}	{name}\n"
    print(output)
except Exception as e:
    print(f"iam.show_domain_role_assignments 查询失败: {e}")
    exit(1)
