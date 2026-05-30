import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListResourceGroupsRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询资源分组列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，范围1-100，默认100")
parser.add_argument("--group_name", type=str, help="资源分组名称，长度1-128")
parser.add_argument("--group_id", type=str, help="资源分组ID，以rg开头，长度24")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID，长度36，也可为0或all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--type", type=str, help="资源分组类型，枚举值：ECS/ELB/VPC/EVS/AS等")
parser.add_argument("--status", type=str, help="资源状态，枚举值：HEALTHY/UNHEALTHY/NOT_EXIST")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListResourceGroupsRequest()
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit
    if args.group_name:
        request.group_name = args.group_name
    if args.group_id:
        request.group_id = args.group_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.type:
        request.type = args.type
    if args.status:
        request.status = args.status

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_resource_groups(request)

    groups = getattr(response, 'resource_groups', []) or []
    count = getattr(response, 'count', 0)

    if not groups:
        print("查询结果为空")
        exit(0)

    output = f"资源分组列表（共{count}个）:\n"
    output += "分组ID\t名称\t类型\t状态\n"
    
    for group in groups:
        group_id = getattr(group, 'group_id', '')
        group_name = getattr(group, 'group_name', '')
        type = getattr(group, 'type', '')
        status = getattr(group, 'status', '')
        output += f"{group_id}\t{group_name}\t{type}\t{status}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_resource_groups 查询失败: {e}")
    exit(1)
