import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowDomainDetectionRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询公网域名的域名诊断")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="域名ID")
parser.add_argument("--type", type=str, help="待诊断记录集的类型: MX/CNAME/TXT")
parser.add_argument("--domain_name", type=str, help="待诊断记录集的域名名称")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    domain_name = getattr(resp, 'domain_name', '')
    rtype = getattr(resp, 'type', '')
    status = getattr(resp, 'status', '')
    print(f"domain_name: {domain_name}\ntype: {rtype}\nstatus: {status}")


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowDomainDetectionRequest()
    request.zone_id = args.zone_id
    if args.type:
        request.type = args.type
    if args.domain_name:
        request.domain_name = args.domain_name

    response = client.show_domain_detection(request)

    render(response)
except Exception as e:
    print(f"dns.show_domain_detection 查询失败: {e}")
    exit(1)
