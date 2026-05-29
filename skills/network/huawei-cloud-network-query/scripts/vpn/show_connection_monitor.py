import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowConnectionMonitorRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 连接监控详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--connection_monitor_id", type=str, required=True, help="连接监控 ID，可通过 list_connection_monitors.py 获取")
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

    request = ShowConnectionMonitorRequest()
    request.connection_monitor_id = args.connection_monitor_id
    response = client.show_connection_monitor(request)
    item = response.connection_monitor
    if not item:
        print("没有找到连接监控")
        exit(0)

    id = getattr(item, 'id', '')
    status = getattr(item, 'status', '')
    vpn_connection_id = getattr(item, 'vpn_connection_id', '')
    type_ = getattr(item, 'type', '')
    source_ip = getattr(item, 'source_ip', '')
    destination_ip = getattr(item, 'destination_ip', '')
    proto_type = getattr(item, 'proto_type', '')

    output = f"id\tstatus\tvpn_connection_id\ttype\tsource_ip\tdestination_ip\tproto_type\n"
    output += f"{id}\t{status}\t{vpn_connection_id}\t{type_}\t{source_ip}\t{destination_ip}\t{proto_type}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_connection_monitor 查询失败: {e}")
    exit(1)
