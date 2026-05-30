import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowP2cVgwRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 P2C VPN 网关详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--p2c_vgw_id", type=str, required=True, help="P2C VPN 网关 ID，可通过 list_p2c_vgws.py 获取")
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

    request = ShowP2cVgwRequest()
    request.p2c_vgw_id = args.p2c_vgw_id
    response = client.show_p2c_vgw(request)
    item = response.p2c_vpn_gateway
    if not item:
        print("没有找到 P2C VPN 网关")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    status = getattr(item, 'status', '')
    vpc_id = getattr(item, 'vpc_id', '')
    connect_subnet = getattr(item, 'connect_subnet', '')
    flavor = getattr(item, 'flavor', '')
    availability_zone_ids = getattr(item, 'availability_zone_ids', []) or []
    eip = getattr(item, 'eip', None)
    eip_id = getattr(eip, 'id', '') if eip else ''
    eip_ip_address = getattr(eip, 'ip_address', '') if eip else ''
    max_connection_number = getattr(item, 'max_connection_number', '')
    current_connection_number = getattr(item, 'current_connection_number', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tags = getattr(item, 'tags', None) or []
    tags_str = '; '.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id\tname\tstatus\tvpc_id\tconnect_subnet\tflavor\tavailability_zone_ids\teip_id\teip_ip_address\tmax_connection_number\tcurrent_connection_number\tenterprise_project_id\ttags\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{status}\t{vpc_id}\t{connect_subnet}\t{flavor}\t{', '.join(availability_zone_ids)}\t{eip_id}\t{eip_ip_address}\t{max_connection_number}\t{current_connection_number}\t{enterprise_project_id}\t{tags_str}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_p2c_vgw 查询失败: {e}")
    exit(1)
