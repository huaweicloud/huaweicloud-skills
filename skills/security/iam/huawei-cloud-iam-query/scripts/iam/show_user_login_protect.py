import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowUserLoginProtectRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询用户登录保护详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, required=True, help="IAM 用户 ID，可通过 keystone_list_users.py 或 list_users_v5.py 获取")
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

    request = ShowUserLoginProtectRequest()
    request.user_id = args.user_id
    response = client.show_user_login_protect(request)
    item = response.login_protect
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"enabled\tuser_id\tverification_method\n"
    enabled = getattr(item, 'enabled', '')
    user_id = getattr(item, 'user_id', '')
    verification_method = getattr(item, 'verification_method', '')
    output += f"{enabled}\t{user_id}\t{verification_method}\n"
    print(output)
except Exception as e:
    print(f"iam.show_user_login_protect 查询失败: {e}")
    exit(1)
