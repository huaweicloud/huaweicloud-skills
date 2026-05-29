import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListApiVersionsRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询API版本信息列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(versions):
    if not versions:
        print("没有找到API版本信息")
        return
    header = "id\tstatus"
    output = header + "\n"
    for v in versions:
        vid = getattr(v, 'id', '')
        status = getattr(v, 'status', '')
        output += f"{vid}\t{status}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ListApiVersionsRequest()

    response = client.list_api_versions(request)

    values = getattr(response, 'versions', None)
    items = getattr(values, 'values', []) if values else []

    if not items:
        print("没有找到API版本信息")
        exit(0)

    render(items)
except Exception as e:
    print(f"dns.list_api_versions 查询失败: {e}")
    exit(1)
