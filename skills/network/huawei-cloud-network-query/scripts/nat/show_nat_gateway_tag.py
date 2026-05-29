import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowNatGatewayTagRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询指定公网NAT网关的标签")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--nat_gateway_id", type=str, required=True, help="公网NAT网关ID，可通过 list_nat_gateways.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 使用 sdk
try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    request = ShowNatGatewayTagRequest()
    request.nat_gateway_id = args.nat_gateway_id
    response = client.show_nat_gateway_tag(request)
    tags = response.tags

    if not tags:
        print(f"该公网NAT网关没有标签")
        exit(0)

    output = f"key\tvalue\n"
    for tag in tags:
        key = getattr(tag, 'key', '')
        value = getattr(tag, 'value', '')
        output += f"{key}\t{value}\n"
    print(output)
except Exception as e:
    print(f"nat.show_nat_gateway_tag 查询失败: {e}")
    exit(1)
