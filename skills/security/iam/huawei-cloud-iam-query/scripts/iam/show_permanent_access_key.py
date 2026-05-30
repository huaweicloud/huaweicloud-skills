import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowPermanentAccessKeyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 永久 AK/SK 详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--access_key", type=str, required=True, help="AK，可通过 list_permanent_access_keys.py 获取")
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

    request = ShowPermanentAccessKeyRequest()
    request.access_key = args.access_key
    response = client.show_permanent_access_key(request)
    item = response.credential

    if not item:
        print(f"没有找到 IAM 永久 AK/SK (区域: {Region}, AK: {args.access_key})")
        exit(0)

    user_id = getattr(item, 'user_id', '')
    access = getattr(item, 'access', '')
    status = getattr(item, 'status', '')
    create_time = getattr(item, 'create_time', '')
    last_use_time = getattr(item, 'last_use_time', '')
    description = getattr(item, 'description', '')
    print(f"user_id\taccess\tstatus\tcreate_time\tlast_use_time\tdescription\n{user_id}\t{access}\t{status}\t{create_time}\t{last_use_time}\t{description}")
except Exception as e:
    print(f"iam.show_permanent_access_key 查询失败: {e}")
    exit(1)
