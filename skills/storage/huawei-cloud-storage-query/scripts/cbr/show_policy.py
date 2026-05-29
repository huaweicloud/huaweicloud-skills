import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowPolicyRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 策略详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--policy_id", type=str, required=True, help="策略ID，可通过 list_policies.py 获取")
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

    request = ShowPolicyRequest()
    request.policy_id = args.policy_id
    response = client.show_policy(request)
    policy = getattr(response, 'policy', None)

    if not policy:
        print(f"没有找到策略 (区域: {Region}, 策略 ID: {args.policy_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(policy, 'id', '')}\n"
    output += f"name: {getattr(policy, 'name', '')}\n"
    output += f"enabled: {getattr(policy, 'enabled', '')}\n"
    output += f"operation_type: {getattr(policy, 'operation_type', '')}\n"
    output += f"policy_type: {getattr(policy, 'policy_type', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_policy 查询失败: {e}")
    exit(1)
