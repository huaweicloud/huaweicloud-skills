import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowApiInfoRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询指定版本号的API版本信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--version", type=str, required=True, help="API版本号，如 v2")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(version_info):
    if not version_info:
        print("没有找到API版本信息")
        return
    vid = getattr(version_info, 'id', '')
    status = getattr(version_info, 'status', '')
    version_val = getattr(version_info, 'version', '')
    min_version = getattr(version_info, 'min_version', '')
    updated = getattr(version_info, 'updated', '')
    links = getattr(version_info, 'links', []) or []
    output = f"id: {vid}\nstatus: {status}\nversion: {version_val}\nmin_version: {min_version}\nupdated: {updated}\n"
    if links:
        output += "links:\n"
        for link in links:
            href = getattr(link, 'href', '')
            rel = getattr(link, 'rel', '')
            output += f"  {rel}: {href}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowApiInfoRequest()
    request.version = args.version

    response = client.show_api_info(request)

    version_info = getattr(response, 'version', None)

    if not version_info:
        print("没有找到API版本信息")
        exit(0)

    render(version_info)
except Exception as e:
    print(f"dns.show_api_info 查询失败: {e}")
    exit(1)
