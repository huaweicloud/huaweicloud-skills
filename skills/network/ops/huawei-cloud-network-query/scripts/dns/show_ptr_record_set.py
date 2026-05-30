import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowPtrRecordSetRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询弹性公网IP的反向解析记录")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--region_id", type=str, required=True, help="区域ID，如 cn-north-4")
parser.add_argument("--floatingip_id", type=str, required=True, help="弹性公网IP的ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    output = ""
    zid = getattr(resp, 'id', '')
    ptrdname = getattr(resp, 'ptrdname', '')
    description = getattr(resp, 'description', '')
    ttl = str(getattr(resp, 'ttl', ''))
    address = getattr(resp, 'address', '')
    status = getattr(resp, 'status', '')
    action = getattr(resp, 'action', '')
    ep_id = getattr(resp, 'enterprise_project_id', '')
    output += f"id: {zid}\nptrdname: {ptrdname}\ndescription: {description}\nttl: {ttl}\naddress: {address}\nstatus: {status}\naction: {action}\nenterprise_project_id: {ep_id}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowPtrRecordSetRequest()
    request.region = args.region_id
    request.floatingip_id = args.floatingip_id

    response = client.show_ptr_record_set(request)

    render(response)
except Exception as e:
    print(f"dns.show_ptr_record_set 查询失败: {e}")
    exit(1)
