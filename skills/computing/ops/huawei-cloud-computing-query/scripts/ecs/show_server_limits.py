import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerLimitsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
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

    request = ShowServerLimitsRequest()
    response = client.show_server_limits(request)
    absolute = response.absolute

    if not absolute:
        print(f"没有找到 ECS 服务器配额 (区域: {Region})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"maxTotalInstances: {getattr(absolute, 'max_total_instances', '')}\n"
    output += f"maxTotalCores: {getattr(absolute, 'max_total_cores', '')}\n"
    output += f"maxTotalRAMSize: {getattr(absolute, 'max_total_ram_size', '')}\n"
    output += f"totalInstancesUsed: {getattr(absolute, 'total_instances_used', '')}\n"
    output += f"totalCoresUsed: {getattr(absolute, 'total_cores_used', '')}\n"
    output += f"totalRAMUsed: {getattr(absolute, 'total_ram_used', '')}\n"
    output += f"maxServerMeta: {getattr(absolute, 'max_server_meta', '')}\n"
    output += f"maxPersonality: {getattr(absolute, 'max_personality', '')}\n"
    output += f"maxPersonalitySize: {getattr(absolute, 'max_personality_size', '')}\n"
    output += f"maxImageMeta: {getattr(absolute, 'max_image_meta', '')}\n"
    output += f"maxSecurityGroups: {getattr(absolute, 'max_security_groups', '')}\n"
    output += f"totalSecurityGroupsUsed: {getattr(absolute, 'total_security_groups_used', '')}\n"
    output += f"maxSecurityGroupRules: {getattr(absolute, 'max_security_group_rules', '')}\n"
    output += f"maxTotalKeypairs: {getattr(absolute, 'max_total_keypairs', '')}\n"
    output += f"maxServerGroups: {getattr(absolute, 'max_server_groups', '')}\n"
    output += f"maxServerGroupMembers: {getattr(absolute, 'max_server_group_members', '')}\n"
    output += f"totalServerGroupsUsed: {getattr(absolute, 'total_server_groups_used', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.server_limits 查询失败: {e}")
    exit(1)
