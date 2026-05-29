import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowRecordSetRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询记录集")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="域名ID")
parser.add_argument("--recordset_id", type=str, required=True, help="记录集ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    output = ""
    rsid = getattr(resp, 'id', '')
    name = getattr(resp, 'name', '')
    description = getattr(resp, 'description', '')
    zone_id = getattr(resp, 'zone_id', '')
    zone_name = getattr(resp, 'zone_name', '')
    rtype = getattr(resp, 'type', '')
    ttl = str(getattr(resp, 'ttl', ''))
    records = getattr(resp, 'records', []) or []
    create_at = getattr(resp, 'create_at', '')
    update_at = getattr(resp, 'update_at', '')
    status = getattr(resp, 'status', '')
    default = getattr(resp, 'default', '')
    project_id = getattr(resp, 'project_id', '')
    bundle = getattr(resp, 'bundle', '')
    output += f"id: {rsid}\nname: {name}\ndescription: {description}\nzone_id: {zone_id}\nzone_name: {zone_name}\ntype: {rtype}\nttl: {ttl}\nstatus: {status}\ndefault: {default}\nproject_id: {project_id}\nbundle: {bundle}\ncreate_at: {create_at}\nupdate_at: {update_at}\n"
    if records:
        output += f"records: {'; '.join(records)}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowRecordSetRequest()
    request.zone_id = args.zone_id
    request.recordset_id = args.recordset_id

    response = client.show_record_set(request)

    render(response)
except Exception as e:
    print(f"dns.show_record_set 查询失败: {e}")
    exit(1)
