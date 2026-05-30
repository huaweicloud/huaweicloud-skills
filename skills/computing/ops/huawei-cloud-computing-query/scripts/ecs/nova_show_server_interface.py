import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import NovaShowServerInterfaceRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器指定网卡详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
parser.add_argument("--port_id", type=str, required=True, help="网卡端口 ID，可通过 list_server_interfaces.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = NovaShowServerInterfaceRequest()
    request.server_id = args.server_id
    request.port_id = args.port_id
    response = client.nova_show_server_interface(request)
    iface = response.interface_attachment

    if not iface:
        print(f"没有找到 ECS 服务器网卡 (区域: {Region}, 服务器 ID: {args.server_id}, 端口 ID: {args.port_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"port_id: {getattr(iface, 'port_id', '')}\n"
    output += f"net_id: {getattr(iface, 'net_id', '')}\n"
    output += f"mac_addr: {getattr(iface, 'mac_addr', '')}\n"
    output += f"port_state: {getattr(iface, 'port_state', '')}\n"
    fixed_ips = getattr(iface, 'fixed_ips', [])
    if fixed_ips:
        for ip_info in fixed_ips:
            ip_address = getattr(ip_info, 'ip_address', '')
            subnet_id = getattr(ip_info, 'subnet_id', '')
            output += f"fixed_ip: {ip_address} (subnet: {subnet_id})\n"
    print(output)
except Exception as e:
    print(f"ecs.nova_show_server_interface 查询失败: {e}")
    exit(1)
