import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowSecurityGroupRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询安全组详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--security_group_id", type=str, required=True, help="安全组 ID（必填），可通过 list_security_groups.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 VPC 客户端")
        exit(-1)

    request = ShowSecurityGroupRequest()
    request.security_group_id = args.security_group_id
    response = client.show_security_group(request)
    item = response.security_group
    if not item:
        print(f"没有找到安全组")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    project_id = getattr(item, 'project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tags = getattr(item, 'tags', [])
    security_group_rules = getattr(item, 'security_group_rules', [])
    output = f"id\tname\tdescription\tproject_id\tcreated_at\tupdated_at\tenterprise_project_id\ttags\tsecurity_group_rules\n"
    output += f"{id}\t{name}\t{description}\t{project_id}\t{created_at}\t{updated_at}\t{enterprise_project_id}\t{tags}\t{len(security_group_rules) if security_group_rules else 0} rules\n"
    print(output)
except Exception as e:
    print(f"vpc.show_security_group 查询失败: {e}")
    exit(1)
