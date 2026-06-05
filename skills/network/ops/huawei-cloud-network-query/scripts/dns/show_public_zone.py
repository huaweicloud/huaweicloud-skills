import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowPublicZoneRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询公网域名")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="公网域名的ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    output = ""
    zid = getattr(resp, 'id', '')
    name = getattr(resp, 'name', '')
    description = getattr(resp, 'description', '')
    email = getattr(resp, 'email', '')
    zone_type = getattr(resp, 'zone_type', '')
    ttl = str(getattr(resp, 'ttl', ''))
    serial = str(getattr(resp, 'serial', ''))
    status = getattr(resp, 'status', '')
    record_num = str(getattr(resp, 'record_num', ''))
    pool_id = getattr(resp, 'pool_id', '')
    project_id = getattr(resp, 'project_id', '')
    created_at = getattr(resp, 'created_at', '')
    updated_at = getattr(resp, 'updated_at', '')
    ep_id = getattr(resp, 'enterprise_project_id', '')
    masters = getattr(resp, 'masters', []) or []
    output += f"id: {zid}\nname: {name}\ndescription: {description}\nemail: {email}\nzone_type: {zone_type}\nttl: {ttl}\nserial: {serial}\nstatus: {status}\nrecord_num: {record_num}\npool_id: {pool_id}\nproject_id: {project_id}\nenterprise_project_id: {ep_id}\ncreated_at: {created_at}\nupdated_at: {updated_at}\n"
    if masters:
        output += f"masters: {', '.join(masters)}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowPublicZoneRequest()
    request.zone_id = args.zone_id

    response = client.show_public_zone(request)

    render(response)
except Exception as e:
    print(f"dns.show_public_zone 查询失败: {e}")
    exit(1)
