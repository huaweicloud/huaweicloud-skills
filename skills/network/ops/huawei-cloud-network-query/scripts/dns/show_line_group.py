import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, resolve_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowLineGroupRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询线路分组")
parser.add_argument("--project_id", type=str, required=False, help="项目 ID，可选；未提供时自动通过 IAM API 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--linegroup_id", type=str, required=True, help="线路分组ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region
args.project_id = resolve_project_id(Region, args.project_id)


def render(resp):
    name = getattr(resp, 'name', '')
    lines = getattr(resp, 'lines', []) or []
    status = getattr(resp, 'status', '')
    description = getattr(resp, 'description', '')
    line_id = getattr(resp, 'line_id', '')
    created_at = getattr(resp, 'created_at', '')
    updated_at = getattr(resp, 'updated_at', '')
    output = f"line_id: {line_id}\nname: {name}\nstatus: {status}\ndescription: {description}\ncreated_at: {created_at}\nupdated_at: {updated_at}\n"
    if lines:
        output += f"lines: {', '.join(lines)}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowLineGroupRequest()
    request.linegroup_id = args.linegroup_id

    response = client.show_line_group(request)

    render(response)
except Exception as e:
    print(f"dns.show_line_group 查询失败: {e}")
    exit(1)
