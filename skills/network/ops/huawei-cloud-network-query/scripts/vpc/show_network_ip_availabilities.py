import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowNetworkIpAvailabilitiesRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询网络IP可用数量")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--network_id", type=str, required=True, help="网络 ID（必填），可通过 list_vpcs.py 获取")
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

    request = ShowNetworkIpAvailabilitiesRequest()
    request.network_id = args.network_id
    response = client.show_network_ip_availabilities(request)
    item = response.network_ip_availability
    if not item:
        print(f"没有找到网络IP可用数量信息")
        exit(0)

    network_id = getattr(item, 'network_id', '')
    network_name = getattr(item, 'network_name', '')
    tenant_id = getattr(item, 'tenant_id', '')
    total_ips = getattr(item, 'total_ips', '')
    used_ips = getattr(item, 'used_ips', '')
    subnet_ip_availability = getattr(item, 'subnet_ip_availability', [])
    output = f"network_id\tnetwork_name\ttenant_id\ttotal_ips\tused_ips\tsubnet_ip_availability\n"
    output += f"{network_id}\t{network_name}\t{tenant_id}\t{total_ips}\t{used_ips}\t{len(subnet_ip_availability) if subnet_ip_availability else 0} subnets\n"
    print(output)
except Exception as e:
    print(f"vpc.show_network_ip_availabilities 查询失败: {e}")
    exit(1)
