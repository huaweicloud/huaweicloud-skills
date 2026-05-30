import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowPrivateZoneNameServerRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询内网域名的名称服务器")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="内网域名的ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(nameservers):
    if not nameservers:
        print("没有找到名称服务器信息")
        return
    header = "hostname\tpriority"
    output = header + "\n"
    for ns in nameservers:
        hostname = getattr(ns, 'hostname', '')
        priority = str(getattr(ns, 'priority', ''))
        address = getattr(ns, 'address', '')
        output += f"{hostname}\t{priority}\t{address}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowPrivateZoneNameServerRequest()
    request.zone_id = args.zone_id

    response = client.show_private_zone_name_server(request)

    nameservers = getattr(response, 'nameservers', []) or []

    if not nameservers:
        print("没有找到名称服务器信息")
        exit(0)

    render(nameservers)
except Exception as e:
    print(f"dns.show_private_zone_name_server 查询失败: {e}")
    exit(1)
