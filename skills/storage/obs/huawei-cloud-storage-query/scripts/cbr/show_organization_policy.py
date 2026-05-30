import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowOrganizationPolicyRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 组织策略详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--organization_policy_id", type=str, required=True, help="组织策略ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowOrganizationPolicyRequest()
    request.organization_policy_id = args.organization_policy_id
    response = client.show_organization_policy(request)
    policy = getattr(response, 'policy', None)

    if not policy:
        print(f"没有找到组织策略 (区域: {Region}, 组织策略 ID: {args.organization_policy_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(policy, 'id', '')}\n"
    output += f"name: {getattr(policy, 'name', '')}\n"
    output += f"description: {getattr(policy, 'description', '')}\n"
    output += f"operation_type: {getattr(policy, 'operation_type', '')}\n"
    output += f"domain_id: {getattr(policy, 'domain_id', '')}\n"
    output += f"domain_name: {getattr(policy, 'domain_name', '')}\n"
    output += f"policy_enabled: {getattr(policy, 'policy_enabled', '')}\n"
    output += f"status: {getattr(policy, 'status', '')}\n"
    output += f"effective_scope: {getattr(policy, 'effective_scope', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_organization_policy 查询失败: {e}")
    exit(1)
