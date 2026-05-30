import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnAccessPolicyRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 访问策略详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vpn_server_id", type=str, required=True, help="VPN 服务端 ID，可通过 list_vpn_servers_by_project.py 获取")
parser.add_argument("--policy_id", type=str, required=True, help="访问策略 ID，可通过 list_vpn_access_policies.py 获取")
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

    request = ShowVpnAccessPolicyRequest()
    request.vpn_server_id = args.vpn_server_id
    request.policy_id = args.policy_id
    response = client.show_vpn_access_policy(request)
    item = response.access_policy
    if not item:
        print("没有找到访问策略")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    type_ = getattr(item, 'type', '')
    user_group_id = getattr(item, 'user_group_id', '')
    user_group_name = getattr(item, 'user_group_name', '')
    description = getattr(item, 'description', '')
    dest_ip_cidrs = getattr(item, 'dest_ip_cidrs', []) or []
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id\tname\ttype\tuser_group_id\tuser_group_name\tdescription\tdest_ip_cidrs\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{type_}\t{user_group_id}\t{user_group_name}\t{description}\t{', '.join(dest_ip_cidrs)}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_vpn_access_policy 查询失败: {e}")
    exit(1)
