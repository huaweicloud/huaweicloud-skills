import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnGatewayCertificateRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 网关证书详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vgw_id", type=str, required=True, help="VPN 网关 ID，可通过 list_vgws.py 获取")
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

    request = ShowVpnGatewayCertificateRequest()
    request.vgw_id = args.vgw_id
    response = client.show_vpn_gateway_certificate(request)
    item = response.certificate
    if not item:
        print("没有找到 VPN 网关证书")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    project_id = getattr(item, 'project_id', '')
    vgw_id = getattr(item, 'vgw_id', '')
    status = getattr(item, 'status', '')
    issuer = getattr(item, 'issuer', '')
    signature_algorithm = getattr(item, 'signature_algorithm', '')
    certificate_serial_number = getattr(item, 'certificate_serial_number', '')
    certificate_subject = getattr(item, 'certificate_subject', '')
    certificate_expire_time = getattr(item, 'certificate_expire_time', '')
    certificate_chain_serial_number = getattr(item, 'certificate_chain_serial_number', '')
    certificate_chain_subject = getattr(item, 'certificate_chain_subject', '')
    certificate_chain_expire_time = getattr(item, 'certificate_chain_expire_time', '')
    enc_certificate_serial_number = getattr(item, 'enc_certificate_serial_number', '')
    enc_certificate_subject = getattr(item, 'enc_certificate_subject', '')
    enc_certificate_expire_time = getattr(item, 'enc_certificate_expire_time', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id\tname\tproject_id\tvgw_id\tstatus\tissuer\tsignature_algorithm\tcertificate_serial_number\tcertificate_subject\tcertificate_expire_time\tcertificate_chain_serial_number\tcertificate_chain_subject\tcertificate_chain_expire_time\tenc_certificate_serial_number\tenc_certificate_subject\tenc_certificate_expire_time\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{project_id}\t{vgw_id}\t{status}\t{issuer}\t{signature_algorithm}\t{certificate_serial_number}\t{certificate_subject}\t{certificate_expire_time}\t{certificate_chain_serial_number}\t{certificate_chain_subject}\t{certificate_chain_expire_time}\t{enc_certificate_serial_number}\t{enc_certificate_subject}\t{enc_certificate_expire_time}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_gateway_certificate 查询失败: {e}")
    exit(1)
