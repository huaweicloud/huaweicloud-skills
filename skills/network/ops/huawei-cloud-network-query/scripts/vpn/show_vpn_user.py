import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnUserRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 用户详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_server_id", type=str, required=True, help="VPN 服务端 ID，可通过 list_vpn_servers_by_project.py 获取")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID，可通过 list_vpn_users.py 获取")
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

    request = ShowVpnUserRequest()
    request.vpn_server_id = args.vpn_server_id
    request.user_id = args.user_id
    response = client.show_vpn_user(request)
    item = response.user
    if not item:
        print("没有找到 VPN 用户")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    user_group_id = getattr(item, 'user_group_id', '')
    user_group_name = getattr(item, 'user_group_name', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    static_ip = getattr(item, 'static_ip', '')

    output = f"id\tname\tdescription\tuser_group_id\tuser_group_name\tcreated_at\tupdated_at\tstatic_ip\n"
    output += f"{id}\t{name}\t{description}\t{user_group_id}\t{user_group_name}\t{created_at}\t{updated_at}\t{static_ip}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_user 查询失败: {e}")
    exit(1)
