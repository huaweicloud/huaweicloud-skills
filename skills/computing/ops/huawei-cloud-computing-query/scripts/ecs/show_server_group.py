import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerGroupRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器组详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_group_id", type=str, required=True, help="服务器组 ID，可通过 list_server_groups.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowServerGroupRequest()
    request.server_group_id = args.server_group_id
    response = client.show_server_group(request)
    group = response.server_group

    if not group:
        print(f"没有找到 ECS 服务器组 (区域: {Region}, 服务器组 ID: {args.server_group_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(group, 'id', '')}\n"
    output += f"name: {getattr(group, 'name', '')}\n"
    members = getattr(group, 'members', '')
    if isinstance(members, list):
        members = ','.join(str(m) for m in members)
    output += f"members: {members}\n"
    policies = getattr(group, 'policies', '')
    if isinstance(policies, list):
        policies = ','.join(str(p) for p in policies)
    output += f"policies: {policies}\n"
    print(output)
except Exception as e:
    print(f"ecs.server_group 查询失败: {e}")
    exit(1)
