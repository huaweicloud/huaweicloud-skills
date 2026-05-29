import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowEndpointRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询终端节点")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--endpoint_id", type=str, required=True, help="终端节点ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(endpoint):
    if not endpoint:
        print("没有找到终端节点信息")
        return
    epid = getattr(endpoint, 'id', '')
    name = getattr(endpoint, 'name', '')
    direction = getattr(endpoint, 'direction', '')
    status = getattr(endpoint, 'status', '')
    created_at = getattr(endpoint, 'created_at', '')
    updated_at = getattr(endpoint, 'updated_at', '')
    ipaddresses = getattr(endpoint, 'ipaddresses', []) or []
    output = f"id: {epid}\nname: {name}\ndirection: {direction}\nstatus: {status}\ncreated_at: {created_at}\nupdated_at: {updated_at}\n"
    if ipaddresses:
        output += "ipaddresses:\n"
        for ipaddr in ipaddresses:
            ipid = getattr(ipaddr, 'id', '')
            ip_info = getattr(ipaddr, 'ip', None)
            ip_val = getattr(ip_info, 'ip', '') if ip_info else ''
            ip_status = getattr(ipaddr, 'status', '')
            output += f"  id={ipid}, ip={ip_val}, status={ip_status}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowEndpointRequest()
    request.endpoint_id = args.endpoint_id

    response = client.show_endpoint(request)

    endpoint = getattr(response, 'endpoint', None)

    if not endpoint:
        print(f"没有找到终端节点 (endpoint_id: {args.endpoint_id})")
        exit(0)

    render(endpoint)
except Exception as e:
    print(f"dns.show_endpoint 查询失败: {e}")
    exit(1)
