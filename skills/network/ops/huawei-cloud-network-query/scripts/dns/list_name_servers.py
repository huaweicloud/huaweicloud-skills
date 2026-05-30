import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListNameServersRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询名称服务器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--type", type=str, choices=["public", "private"], help="域名类型: public/private")
parser.add_argument("--ns_region", type=str, help="区域，如 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(nameservers):
    if not nameservers:
        print("没有找到名称服务器信息")
        return
    for ns in nameservers:
        ns_type = getattr(ns, 'type', '')
        ns_region = getattr(ns, 'region', '')
        ns_records = getattr(ns, 'ns_records', []) or []
        print(f"type: {ns_type}, region: {ns_region}")
        if ns_records:
            header = "  hostname\tpriority\taddress"
            print(header)
            for record in ns_records:
                hostname = getattr(record, 'hostname', '')
                priority = str(getattr(record, 'priority', ''))
                address = getattr(record, 'address', '')
                print(f"  {hostname}\t{priority}\t{address}")
        print()


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ListNameServersRequest()
    if args.type:
        request.type = args.type
    if args.ns_region:
        request.region = args.ns_region

    response = client.list_name_servers(request)

    nameservers = getattr(response, 'nameservers', []) or []

    if not nameservers:
        print("没有找到名称服务器信息")
        exit(0)

    render(nameservers)
except Exception as e:
    print(f"dns.list_name_servers 查询失败: {e}")
    exit(1)
