import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetPolicyVersionV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询策略版本详情 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--policy_id", type=str, required=True, help="身份策略 ID，可通过 list_policies_v5.py 获取")
parser.add_argument("--version_id", type=str, required=True, help="身份策略版本号，以 v 开头后跟数字，如 v1，可通过 list_policy_versions_v5.py 获取")
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

    request = GetPolicyVersionV5Request()
    request.policy_id = args.policy_id
    request.version_id = args.version_id
    response = client.get_policy_version_v5(request)
    item = response.policy_version
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"version_id	is_default	created_at	document\n"
    version_id = getattr(item, 'version_id', '')
    is_default = getattr(item, 'is_default', '')
    created_at = getattr(item, 'created_at', '')
    document = getattr(item, 'document', '')
    output += f"{version_id}	{is_default}	{created_at}	{document}\n"
    print(output)
except Exception as e:
    print(f"iam.get_policy_version_v5 查询失败: {e}")
    exit(1)
