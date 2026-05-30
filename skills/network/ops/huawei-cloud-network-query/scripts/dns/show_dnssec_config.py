import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowDnssecConfigRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询DNSSEC")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="域名ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    output = ""
    zone_name = getattr(resp, 'zone_name', '')
    key_tag = str(getattr(resp, 'key_tag', ''))
    flag = str(getattr(resp, 'flag', ''))
    digest_algorithm = str(getattr(resp, 'digest_algorithm', ''))
    digest_type = str(getattr(resp, 'digest_type', ''))
    digest = getattr(resp, 'digest', '')
    signature = getattr(resp, 'signature', '')
    signature_type = getattr(resp, 'signature_type', '')
    ksk_public_key = getattr(resp, 'ksk_public_key', '')
    ds_record = getattr(resp, 'ds_record', '')
    created_at = getattr(resp, 'created_at', '')
    updated_at = getattr(resp, 'updated_at', '')
    status = getattr(resp, 'status', '')
    output += f"zone_name: {zone_name}\nkey_tag: {key_tag}\nflag: {flag}\ndigest_algorithm: {digest_algorithm}\ndigest_type: {digest_type}\ndigest: {digest}\nsignature: {signature}\nsignature_type: {signature_type}\nksk_public_key: {ksk_public_key}\nds_record: {ds_record}\nstatus: {status}\ncreated_at: {created_at}\nupdated_at: {updated_at}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowDnssecConfigRequest()
    request.zone_id = args.zone_id

    response = client.show_dnssec_config(request)

    render(response)
except Exception as e:
    print(f"dns.show_dnssec_config 查询失败: {e}")
    exit(1)
