import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowRetrievalVerificationRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询公网域名找回结果")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, required=True, help="找回任务ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    zid = getattr(resp, 'id', '')
    status = getattr(resp, 'status', '')
    updated_at = getattr(resp, 'updated_at', '')
    print(f"id: {zid}\nstatus: {status}\nupdated_at: {updated_at}")


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowRetrievalVerificationRequest()
    request.id = args.id

    response = client.show_retrieval_verification(request)

    render(response)
except Exception as e:
    print(f"dns.show_retrieval_verification 查询失败: {e}")
    exit(1)
