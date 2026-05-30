import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneShowServiceRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询服务详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--service_id", type=str, required=True, help="服务 ID，可通过 keystone_list_services.py 获取")
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

    request = KeystoneShowServiceRequest()
    request.service_id = args.service_id
    response = client.keystone_show_service(request)
    item = response.service
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"id	name	type	enabled	description	links\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    type = getattr(item, 'type', '')
    enabled = getattr(item, 'enabled', '')
    description = getattr(item, 'description', '')
    links = repr(getattr(item, 'links', ''))
    output += f"{id}	{name}	{type}	{enabled}	{description}	{links}\n"
    print(output)
except Exception as e:
    print(f"iam.keystone_show_service 查询失败: {e}")
    exit(1)
