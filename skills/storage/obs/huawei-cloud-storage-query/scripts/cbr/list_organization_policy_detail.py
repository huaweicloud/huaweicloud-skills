import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListOrganizationPolicyDetailRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询组织策略部署状态列表")
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

    request = ListOrganizationPolicyDetailRequest()
    request.organization_policy_id = args.organization_policy_id

    response = client.list_organization_policy_detail(request)
    policies = getattr(response, 'policies', []) or []
    count = getattr(response, 'count', 0)

    if not policies:
        print(f"没有找到组织策略详情 (区域: {Region})")
        exit(0)

    output = f"policy_id\tdomain_id\tproject_id\tstatus\n"
    for policy in policies:
        policy_id = getattr(policy, 'policy_id', '')
        domain_id = getattr(policy, 'domain_id', '')
        project_id = getattr(policy, 'project_id', '')
        status = getattr(policy, 'status', '')
        output += f"{policy_id}\t{domain_id}\t{project_id}\t{status}\n"
    print(output)
except Exception as e:
    print(f"cbr.list_organization_policy_detail 查询失败: {e}")
    exit(1)
