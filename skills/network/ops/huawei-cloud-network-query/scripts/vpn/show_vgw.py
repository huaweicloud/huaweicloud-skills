import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVgwRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 网关详情")
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

    request = ShowVgwRequest()
    request.vgw_id = args.vgw_id
    response = client.show_vgw(request)
    item = response.vpn_gateway
    if not item:
        print("没有找到 VPN 网关")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    status = getattr(item, 'status', '')
    attachment_type = getattr(item, 'attachment_type', '')
    ip_version = getattr(item, 'ip_version', '')
    certificate_id = getattr(item, 'certificate_id', '')
    er_id = getattr(item, 'er_id', '')
    vpc_id = getattr(item, 'vpc_id', '')
    local_subnets = getattr(item, 'local_subnets', []) or []
    connect_subnet = getattr(item, 'connect_subnet', '')
    network_type = getattr(item, 'network_type', '')
    bgp_asn = getattr(item, 'bgp_asn', '')
    flavor = getattr(item, 'flavor', '')
    connection_number = getattr(item, 'connection_number', '')
    used_connection_number = getattr(item, 'used_connection_number', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    ha_mode = getattr(item, 'ha_mode', '')
    eip1 = getattr(item, 'eip1', None)
    eip1_id = getattr(eip1, 'id', '') if eip1 else ''
    eip1_ip_address = getattr(eip1, 'ip_address', '') if eip1 else ''
    eip2 = getattr(item, 'eip2', None)
    eip2_id = getattr(eip2, 'id', '') if eip2 else ''
    eip2_ip_address = getattr(eip2, 'ip_address', '') if eip2 else ''
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    tags = getattr(item, 'tags', None) or []
    tags_str = '; '.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)

    output = f"id\tname\tstatus\tattachment_type\tip_version\tcertificate_id\ter_id\tvpc_id\tlocal_subnets\tconnect_subnet\tnetwork_type\tbgp_asn\tflavor\tconnection_number\tused_connection_number\tenterprise_project_id\tha_mode\teip1_id\teip1_ip_address\teip2_id\teip2_ip_address\tcreated_at\tupdated_at\ttags\n"
    output += f"{id}\t{name}\t{status}\t{attachment_type}\t{ip_version}\t{certificate_id}\t{er_id}\t{vpc_id}\t{', '.join(local_subnets)}\t{connect_subnet}\t{network_type}\t{bgp_asn}\t{flavor}\t{connection_number}\t{used_connection_number}\t{enterprise_project_id}\t{ha_mode}\t{eip1_id}\t{eip1_ip_address}\t{eip2_id}\t{eip2_ip_address}\t{created_at}\t{updated_at}\t{tags_str}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vgw 查询失败: {e}")
    exit(1)
