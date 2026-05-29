import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ShowUserV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 用户详情 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID，可通过 list_users_v5.py 获取")
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

    request = ShowUserV5Request()
    request.user_id = args.user_id
    response = client.show_user_v5(request)
    item = response.user

    if not item:
        print(f"没有找到 IAM 用户 (区域: {Region}, 用户 ID: {args.user_id})")
        exit(0)

    user_id = getattr(item, 'user_id', '')
    user_name = getattr(item, 'user_name', '')
    enabled = getattr(item, 'enabled', '')
    is_root_user = getattr(item, 'is_root_user', '')
    description = getattr(item, 'description', '')
    created_at = getattr(item, 'created_at', '')
    urn = getattr(item, 'urn', '')
    tags = getattr(item, 'tags', None)
    tags_str = ';'.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags) if tags else ''
    print(f"user_id\tuser_name\tenabled\tis_root_user\tdescription\tcreated_at\turn\ttags\n{user_id}\t{user_name}\t{enabled}\t{is_root_user}\t{description}\t{created_at}\t{urn}\t{tags_str}")
except Exception as e:
    print(f"iam.show_user_v5 查询失败: {e}")
    exit(1)
