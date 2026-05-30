import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneShowVersionRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 Keystone 版本详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")

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

    request = KeystoneShowVersionRequest()

    response = client.keystone_show_version(request)
    item = response.version
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"id	status	updated	links	media_types\n"
    id = getattr(item, 'id', '')
    status = getattr(item, 'status', '')
    updated = getattr(item, 'updated', '')
    links = repr(getattr(item, 'links', ''))
    media_types = repr(getattr(item, 'media_types', ''))
    output += f"{id}	{status}	{updated}	{links}	{media_types}\n"
    print(output)
except Exception as e:
    print(f"iam.keystone_show_version 查询失败: {e}")
    exit(1)
