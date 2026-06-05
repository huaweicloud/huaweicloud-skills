import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ShowAccessKeyLastUsedV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM AK/SK 最后使用时间 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID，可通过 list_users_v5.py 获取")
parser.add_argument("--access_key_id", type=str, required=True, help="AK ID")
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

    request = ShowAccessKeyLastUsedV5Request()
    request.user_id = args.user_id
    request.access_key_id = args.access_key_id
    response = client.show_access_key_last_used_v5(request)
    item = response.access_key_last_used

    if not item:
        print(f"没有找到 IAM AK/SK 最后使用时间 (区域: {Region}, 用户 ID: {args.user_id}, AK ID: {args.access_key_id})")
        exit(0)

    last_used_at = getattr(item, 'last_used_at', '')
    print(f"last_used_at\n{last_used_at}")
except Exception as e:
    print(f"iam.show_access_key_last_used_v5 查询失败: {e}")
    exit(1)
