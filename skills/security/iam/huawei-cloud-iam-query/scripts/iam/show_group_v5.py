import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ShowGroupV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 用户组详情 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--group_id", type=str, required=True, help="用户组 ID，可通过 list_groups_v5.py 获取")
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

    request = ShowGroupV5Request()
    request.group_id = args.group_id
    response = client.show_group_v5(request)
    item = response.group

    if not item:
        print(f"没有找到 IAM 用户组 (区域: {Region}, 用户组 ID: {args.group_id})")
        exit(0)

    group_id = getattr(item, 'group_id', '')
    group_name = getattr(item, 'group_name', '')
    description = getattr(item, 'description', '')
    created_at = getattr(item, 'created_at', '')
    urn = getattr(item, 'urn', '')
    print(f"group_id\tgroup_name\tdescription\tcreated_at\turn\n{group_id}\t{group_name}\t{description}\t{created_at}\t{urn}")
except Exception as e:
    print(f"iam.show_group_v5 查询失败: {e}")
    exit(1)
