import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowPtrRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询弹性公网IP的反向解析记录")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--ptr_id", type=str, required=True, help="反向解析ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    output = ""
    zid = getattr(resp, 'id', '')
    publicip = getattr(resp, 'publicip', None)
    ptrdnames = getattr(resp, 'ptrdnames', '') or ''
    description = getattr(resp, 'description', '')
    ttl = str(getattr(resp, 'ttl', ''))
    status = getattr(resp, 'status', '')
    ep_id = getattr(resp, 'enterprise_project_id', '')
    output += f"id: {zid}\nptrdnames: {ptrdnames}\ndescription: {description}\nttl: {ttl}\nstatus: {status}\nenterprise_project_id: {ep_id}\n"
    if publicip:
        pip_id = getattr(publicip, 'id', '')
        pip_address = getattr(publicip, 'address', '')
        pip_type = getattr(publicip, 'type', '')
        output += f"publicip_id: {pip_id}\npublicip_address: {pip_address}\npublicip_type: {pip_type}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowPtrRequest()
    request.ptr_id = args.ptr_id

    response = client.show_ptr(request)

    render(response)
except Exception as e:
    print(f"dns.show_ptr 查询失败: {e}")
    exit(1)
