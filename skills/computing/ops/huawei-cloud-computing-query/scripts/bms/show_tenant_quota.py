import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowTenantQuotaRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询裸金属服务器租户配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


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
    request = ShowTenantQuotaRequest()

    response = client.show_tenant_quota(request)
    absolute = response.absolute

    if not absolute:
        print(f"没有找到配额信息 (区域: {Region})")
        exit(0)

    # 渲染
    output = ""
    output += f"maxTotalInstances: {getattr(absolute, 'max_total_instances', 0)}\n"
    output += f"totalInstancesUsed: {getattr(absolute, 'total_instances_used', 0)}\n"
    output += f"maxTotalCores: {getattr(absolute, 'max_total_cores', 0)}\n"
    output += f"totalCoresUsed: {getattr(absolute, 'total_cores_used', 0)}\n"
    output += f"maxTotalRAMSize: {getattr(absolute, 'max_total_ram_size', 0)}\n"
    output += f"totalRAMUsed: {getattr(absolute, 'total_ram_used', 0)}\n"
    output += f"maxTotalKeypairs: {getattr(absolute, 'max_total_keypairs', 0)}\n"
    output += f"maxServerMeta: {getattr(absolute, 'max_server_meta', 0)}\n"
    output += f"maxPersonality: {getattr(absolute, 'max_personality', 0)}\n"
    output += f"maxPersonalitySize: {getattr(absolute, 'max_personality_size', 0)}\n"
    output += f"maxServerGroups: {getattr(absolute, 'max_server_groups', 0)}\n"
    output += f"maxServerGroupMembers: {getattr(absolute, 'max_server_group_members', 0)}\n"
    output += f"totalServerGroupsUsed: {getattr(absolute, 'total_server_groups_used', 0)}\n"
    output += f"maxSecurityGroups: {getattr(absolute, 'max_security_groups', 0)}\n"
    output += f"maxSecurityGroupRules: {getattr(absolute, 'max_security_group_rules', 0)}\n"
    output += f"totalSecurityGroupsUsed: {getattr(absolute, 'total_security_groups_used', 0)}\n"
    output += f"maxTotalFloatingIps: {getattr(absolute, 'max_total_floating_ips', 0)}\n"
    output += f"totalFloatingIpsUsed: {getattr(absolute, 'total_floating_ips_used', 0)}\n"
    output += f"maxImageMeta: {getattr(absolute, 'max_image_meta', 0)}\n"

    print(output)
except Exception as e:
    print(f"bms.show_tenant_quota 查询失败: {e}")
    exit(1)
