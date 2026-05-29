import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnConnectionsLogConfigRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 连接日志配置")
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

    request = ShowVpnConnectionsLogConfigRequest()
    request.p2c_vgw_id = args.p2c_vgw_id
    response = client.show_vpn_connections_log_config(request)
    item = response.log_config
    if not item:
        print("没有找到连接日志配置")
        exit(0)

    log_group_id = getattr(item, 'log_group_id', '')
    log_stream_id = getattr(item, 'log_stream_id', '')

    output = f"log_group_id\tlog_stream_id\n"
    output += f"{log_group_id}\t{log_stream_id}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_connections_log_config 查询失败: {e}")
    exit(1)
