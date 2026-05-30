import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowZoneNameServerRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询公网域名的DNS服务器地址")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_name", type=str, required=True, help="公网域名名称")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    all_hw_dns = getattr(resp, 'all_hw_dns', '')
    include_hw_dns = getattr(resp, 'include_hw_dns', '')
    domain_name = getattr(resp, 'domain_name', '')
    dns_servers = getattr(resp, 'dns_servers', []) or []
    expected_dns_servers = getattr(resp, 'expected_dns_servers', []) or []
    output = f"domain_name: {domain_name}\nall_hw_dns: {all_hw_dns}\ninclude_hw_dns: {include_hw_dns}\n"
    if dns_servers:
        output += "dns_servers:\n"
        for ns in dns_servers:
            hostname = getattr(ns, 'hostname', '')
            priority = str(getattr(ns, 'priority', ''))
            output += f"  {hostname} (priority: {priority})\n"
    if expected_dns_servers:
        output += "expected_dns_servers:\n"
        for ns in expected_dns_servers:
            hostname = getattr(ns, 'hostname', '')
            priority = str(getattr(ns, 'priority', ''))
            output += f"  {hostname} (priority: {priority})\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowZoneNameServerRequest()
    request.domain_name = args.domain_name

    response = client.show_zone_name_server(request)

    render(response)
except Exception as e:
    print(f"dns.show_zone_name_server 查询失败: {e}")
    exit(1)
