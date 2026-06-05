import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneValidateTokenRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="校验 Token (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--x_subject_token", type=str, required=True, help="待校验的 Token")
parser.add_argument("--nocatalog", action="store_true", help="不返回 catalog 信息")
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

    request = KeystoneValidateTokenRequest()
    request.x_subject_token = args.x_subject_token
    if args.nocatalog:
        request.nocatalog = True
    response = client.keystone_validate_token(request)
    item = response.token
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"methods	expires_at	issued_at\n"
    methods = getattr(item, 'methods', '')
    expires_at = getattr(item, 'expires_at', '')
    issued_at = getattr(item, 'issued_at', '')
    output += f"{methods}	{expires_at}	{issued_at}\n"
    print(output)
except Exception as e:
    print(f"iam.keystone_validate_token 查询失败: {e}")
    exit(1)
