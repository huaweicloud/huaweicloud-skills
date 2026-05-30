import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListEndpointIpaddressesRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询IP地址列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--endpoint_id", type=str, required=True, help="终端节点ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(ipaddresses):
    if not ipaddresses:
        print("没有找到IP地址信息")
        return
    header = "id\tip\tstatus\tcreated_at\tupdated_at"
    output = header + "\n"
    for ipaddr in ipaddresses:
        ipid = getattr(ipaddr, 'id', '')
        ip_info = getattr(ipaddr, 'ip', None)
        ip_val = getattr(ip_info, 'ip', '') if ip_info else ''
        status = getattr(ipaddr, 'status', '')
        created_at = getattr(ipaddr, 'created_at', '')
        updated_at = getattr(ipaddr, 'updated_at', '')
        output += f"{ipid}\t{ip_val}\t{status}\t{created_at}\t{updated_at}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ListEndpointIpaddressesRequest()
    request.endpoint_id = args.endpoint_id

    response = client.list_endpoint_ipaddresses(request)

    ipaddresses = getattr(response, 'ipaddresses', []) or []

    if not ipaddresses:
        print(f"没有找到IP地址 (endpoint_id: {args.endpoint_id})")
        exit(0)

    render(ipaddresses)
except Exception as e:
    print(f"dns.list_endpoint_ipaddresses 查询失败: {e}")
    exit(1)
