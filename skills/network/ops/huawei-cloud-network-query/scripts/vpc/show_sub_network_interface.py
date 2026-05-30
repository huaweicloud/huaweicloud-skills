import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowSubNetworkInterfaceRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询子网络接口详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--sub_network_interface_id", type=str, required=True, help="子网络接口 ID（必填），可通过 list_sub_network_interfaces.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 VPC 客户端")
        exit(-1)

    request = ShowSubNetworkInterfaceRequest()
    request.sub_network_interface_id = args.sub_network_interface_id
    response = client.show_sub_network_interface(request)
    item = response.sub_network_interface
    if not item:
        print(f"没有找到子网络接口")
        exit(0)

    id = getattr(item, 'id', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    private_ip_address = getattr(item, 'private_ip_address', '')
    ipv6_ip_address = getattr(item, 'ipv6_ip_address', '')
    mac_address = getattr(item, 'mac_address', '')
    parent_device_id = getattr(item, 'parent_device_id', '')
    parent_id = getattr(item, 'parent_id', '')
    description = getattr(item, 'description', '')
    vpc_id = getattr(item, 'vpc_id', '')
    vlan_id = getattr(item, 'vlan_id', '')
    security_groups = getattr(item, 'security_groups', [])
    tags = getattr(item, 'tags', [])
    project_id = getattr(item, 'project_id', '')
    created_at = getattr(item, 'created_at', '')
    state = getattr(item, 'state', '')
    output = f"id\tvirsubnet_id\tprivate_ip_address\tipv6_ip_address\tmac_address\tparent_device_id\tparent_id\tdescription\tvpc_id\tvlan_id\tsecurity_groups\ttags\tproject_id\tcreated_at\tstate\n"
    output += f"{id}\t{virsubnet_id}\t{private_ip_address}\t{ipv6_ip_address}\t{mac_address}\t{parent_device_id}\t{parent_id}\t{description}\t{vpc_id}\t{vlan_id}\t{security_groups}\t{tags}\t{project_id}\t{created_at}\t{state}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_sub_network_interface 查询失败: {e}")
    exit(1)
