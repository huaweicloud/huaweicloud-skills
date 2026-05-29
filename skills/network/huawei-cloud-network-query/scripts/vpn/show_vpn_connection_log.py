import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnConnectionLogRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 连接日志")
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

    request = ShowVpnConnectionLogRequest()
    request.vpn_connection_id = args.vpn_connection_id
    response = client.show_vpn_connection_log(request)
    logs = response.logs
    if not logs:
        print("没有找到日志")
        exit(0)

    output = f"time\traw_message\n"
    for log in logs:
        time_ = getattr(log, 'time', '')
        raw_message = getattr(log, 'raw_message', '')
        output += f"{time_}\t{raw_message}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_connection_log 查询失败: {e}")
    exit(1)
