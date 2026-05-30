import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowDomainQuotaRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询租户配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, required=True, help="租户ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(quotas):
    if not quotas:
        print("没有找到配额信息")
        return
    header = "quota_key\tquota_limit\tused\tunit"
    output = header + "\n"
    for q in quotas:
        quota_key = getattr(q, 'quota_key', '')
        quota_limit = str(getattr(q, 'quota_limit', ''))
        used = str(getattr(q, 'used', ''))
        unit = getattr(q, 'unit', '')
        output += f"{quota_key}\t{quota_limit}\t{used}\t{unit}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowDomainQuotaRequest()
    request.domain_id = args.domain_id

    response = client.show_domain_quota(request)

    quotas = getattr(response, 'quotas', []) or []

    if not quotas:
        print("没有找到配额信息")
        exit(0)

    render(quotas)
except Exception as e:
    print(f"dns.show_domain_quota 查询失败: {e}")
    exit(1)
