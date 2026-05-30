import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowResourceTagRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询指定实例的标签信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resource_type", type=str, required=True, choices=["DNS-public_zone", "DNS-private_zone", "DNS-public_recordset", "DNS-private_recordset", "DNS-ptr_record"], help="资源类型: DNS-public_zone/DNS-private_zone/DNS-public_recordset/DNS-private_recordset/DNS-ptr_record")
parser.add_argument("--resource_id", type=str, required=True, help="资源ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(tags):
    if not tags:
        print("没有找到标签信息")
        return
    header = "key\tvalue"
    output = header + "\n"
    for tag in tags:
        key = getattr(tag, 'key', '')
        value = getattr(tag, 'value', '')
        output += f"{key}\t{value}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowResourceTagRequest()
    request.resource_type = args.resource_type
    request.resource_id = args.resource_id

    response = client.show_resource_tag(request)

    tags = getattr(response, 'tags', []) or []

    if not tags:
        print(f"没有找到标签 (resource_type: {args.resource_type}, resource_id: {args.resource_id})")
        exit(0)

    render(tags)
except Exception as e:
    print(f"dns.show_resource_tag 查询失败: {e}")
    exit(1)
