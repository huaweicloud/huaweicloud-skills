import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowClientCaRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户端 CA 证书详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_server_id", type=str, required=True, help="VPN 服务端 ID，可通过 list_vpn_servers_by_project.py 获取")
parser.add_argument("--client_ca_certificate_id", type=str, required=True, help="客户端 CA 证书 ID")
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

    request = ShowClientCaRequest()
    request.vpn_server_id = args.vpn_server_id
    request.client_ca_certificate_id = args.client_ca_certificate_id
    response = client.show_client_ca(request)
    item = response.client_ca_certificate
    if not item:
        print("没有找到客户端 CA 证书")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    issuer = getattr(item, 'issuer', '')
    subject = getattr(item, 'subject', '')
    serial_number = getattr(item, 'serial_number', '')
    expiration_time = getattr(item, 'expiration_time', '')
    signature_algorithm = getattr(item, 'signature_algorithm', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id\tname\tissuer\tsubject\tserial_number\texpiration_time\tsignature_algorithm\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{issuer}\t{subject}\t{serial_number}\t{expiration_time}\t{signature_algorithm}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_client_ca 查询失败: {e}")
    exit(1)
