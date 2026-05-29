import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowResourceTagsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询资源标签")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resource_type", type=str, required=True, help="资源类型 (必填)，如 vpn-gateway, vpn-connection, customer-gateway, p2c-vpn-gateway")
parser.add_argument("--resource_id", type=str, required=True, help="资源 ID，根据资源类型可通过相应 list 脚本获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    request = ShowResourceTagsRequest()
    request.resource_type = args.resource_type
    request.resource_id = args.resource_id
    response = client.show_resource_tags(request)
    tags = response.tags

    if not tags:
        print(f"没有找到资源标签 (区域: {Region}, 资源类型: {args.resource_type}, 资源 ID: {args.resource_id})")
        exit(0)

    output = f"key\tvalue\n"
    for tag in tags:
        key = getattr(tag, 'key', '')
        value = getattr(tag, 'value', '')
        output += f"{key}\t{value}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_resource_tags 查询失败: {e}")
    exit(1)
