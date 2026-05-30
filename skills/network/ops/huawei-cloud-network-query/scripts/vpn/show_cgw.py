import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowCgwRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询对端网关详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--customer_gateway_id", type=str, required=True, help="对端网关 ID，可通过 list_cgws.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    request = ShowCgwRequest()
    request.customer_gateway_id = args.customer_gateway_id
    response = client.show_cgw(request)
    item = response.customer_gateway
    if not item:
        print("没有找到对端网关")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    bgp_asn = getattr(item, 'bgp_asn', '')
    id_type = getattr(item, 'id_type', '')
    id_value = getattr(item, 'id_value', '')
    ca_certificate = getattr(item, 'ca_certificate', None)
    ca_cert_id = getattr(ca_certificate, 'id', '') if ca_certificate else ''
    ca_cert_serial_number = getattr(ca_certificate, 'serial_number', '') if ca_certificate else ''
    ca_cert_issuer = getattr(ca_certificate, 'issuer', '') if ca_certificate else ''
    ca_cert_subject = getattr(ca_certificate, 'subject', '') if ca_certificate else ''
    ca_cert_expire_time = getattr(ca_certificate, 'expire_time', '') if ca_certificate else ''
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    tags = getattr(item, 'tags', None) or []
    tags_str = '; '.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)

    output = f"id\tname\tbgp_asn\tid_type\tid_value\tca_cert_id\tca_cert_serial_number\tca_cert_issuer\tca_cert_subject\tca_cert_expire_time\tcreated_at\tupdated_at\ttags\n"
    output += f"{id}\t{name}\t{bgp_asn}\t{id_type}\t{id_value}\t{ca_cert_id}\t{ca_cert_serial_number}\t{ca_cert_issuer}\t{ca_cert_subject}\t{ca_cert_expire_time}\t{created_at}\t{updated_at}\t{tags_str}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_cgw 查询失败: {e}")
    exit(1)
