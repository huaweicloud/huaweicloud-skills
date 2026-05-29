import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneShowPermissionRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询权限详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--role_id", type=str, required=True, help="权限 ID，可通过 keystone_list_permissions.py 获取")
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

    request = KeystoneShowPermissionRequest()
    request.role_id = args.role_id
    response = client.keystone_show_permission(request)
    item = response.role
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"id	name	display_name	type	catalog	description	domain_id	flag	description_cn	links	policy	updated_time	created_time\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    display_name = getattr(item, 'display_name', '')
    type = getattr(item, 'type', '')
    catalog = getattr(item, 'catalog', '')
    description = getattr(item, 'description', '')
    domain_id = getattr(item, 'domain_id', '')
    flag = getattr(item, 'flag', '')
    description_cn = getattr(item, 'description_cn', '')
    links = repr(getattr(item, 'links', ''))
    policy = repr(getattr(item, 'policy', ''))
    updated_time = getattr(item, 'updated_time', '')
    created_time = getattr(item, 'created_time', '')
    output += f"{id}	{name}	{display_name}	{type}	{catalog}	{description}	{domain_id}	{flag}	{description_cn}	{links}	{policy}	{updated_time}	{created_time}\n"
    print(output)
except Exception as e:
    print(f"iam.keystone_show_permission 查询失败: {e}")
    exit(1)
