import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetPolicyV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询策略详情 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--policy_id", type=str, required=True, help="策略 ID，可通过 list_policies_v5.py 获取")
parser.add_argument("--x_language", type=str, choices=["zh-cn", "en-us"], help="语言，zh-cn 或 en-us")
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

    request = GetPolicyV5Request()
    request.policy_id = args.policy_id
    if args.x_language:
        request.x_language = args.x_language
    response = client.get_policy_v5(request)
    item = response.policy
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"policy_id	policy_name	policy_type	urn	path	description	default_version_id	attachment_count	created_at	updated_at\n"
    policy_id = getattr(item, 'policy_id', '')
    policy_name = getattr(item, 'policy_name', '')
    policy_type = getattr(item, 'policy_type', '')
    urn = getattr(item, 'urn', '')
    path = getattr(item, 'path', '')
    description = getattr(item, 'description', '')
    default_version_id = getattr(item, 'default_version_id', '')
    attachment_count = getattr(item, 'attachment_count', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output += f"{policy_id}	{policy_name}	{policy_type}	{urn}	{path}	{description}	{default_version_id}	{attachment_count}	{created_at}	{updated_at}\n"
    print(output)
except Exception as e:
    print(f"iam.get_policy_v5 查询失败: {e}")
    exit(1)
