import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnConnectionRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 连接详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_connection_id", type=str, required=True, help="VPN 连接 ID，可通过 list_vpn_connections.py 获取")
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

    request = ShowVpnConnectionRequest()
    request.vpn_connection_id = args.vpn_connection_id
    response = client.show_vpn_connection(request)
    item = response.vpn_connection
    if not item:
        print("没有找到 VPN 连接")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    status = getattr(item, 'status', '')
    vgw_id = getattr(item, 'vgw_id', '')
    vgw_ip = getattr(item, 'vgw_ip', '')
    style = getattr(item, 'style', '')
    cgw_id = getattr(item, 'cgw_id', '')
    peer_subnets = getattr(item, 'peer_subnets', []) or []
    tunnel_local_address = getattr(item, 'tunnel_local_address', '')
    tunnel_peer_address = getattr(item, 'tunnel_peer_address', '')
    enable_nqa = getattr(item, 'enable_nqa', '')
    enable_hub = getattr(item, 'enable_hub', '')
    connection_monitor_id = getattr(item, 'connection_monitor_id', '')
    ha_role = getattr(item, 'ha_role', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tags = getattr(item, 'tags', None) or []
    tags_str = '; '.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)

    output = f"id\tname\tstatus\tvgw_id\tvgw_ip\tstyle\tcgw_id\tpeer_subnets\ttunnel_local_address\ttunnel_peer_address\tenable_nqa\tenable_hub\tconnection_monitor_id\tha_role\tcreated_at\tupdated_at\tenterprise_project_id\ttags\n"
    output += f"{id}\t{name}\t{status}\t{vgw_id}\t{vgw_ip}\t{style}\t{cgw_id}\t{', '.join(peer_subnets)}\t{tunnel_local_address}\t{tunnel_peer_address}\t{enable_nqa}\t{enable_hub}\t{connection_monitor_id}\t{ha_role}\t{created_at}\t{updated_at}\t{enterprise_project_id}\t{tags_str}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_connection 查询失败: {e}")
    exit(1)
