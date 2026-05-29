import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowSubnetRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询子网详情（v2）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--subnet_id", type=str, required=True, help="子网 ID（必填），可通过 list_subnets.py 获取")
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

    request = ShowSubnetRequest()
    request.subnet_id = args.subnet_id
    response = client.show_subnet(request)
    item = response.subnet
    if not item:
        print(f"没有找到子网")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    cidr = getattr(item, 'cidr', '')
    gateway_ip = getattr(item, 'gateway_ip', '')
    ipv6_enable = getattr(item, 'ipv6_enable', '')
    cidr_v6 = getattr(item, 'cidr_v6', '')
    gateway_ip_v6 = getattr(item, 'gateway_ip_v6', '')
    dhcp_enable = getattr(item, 'dhcp_enable', '')
    primary_dns = getattr(item, 'primary_dns', '')
    secondary_dns = getattr(item, 'secondary_dns', '')
    dns_list = getattr(item, 'dns_list', [])
    availability_zone = getattr(item, 'availability_zone', '')
    vpc_id = getattr(item, 'vpc_id', '')
    status = getattr(item, 'status', '')
    neutron_network_id = getattr(item, 'neutron_network_id', '')
    neutron_subnet_id = getattr(item, 'neutron_subnet_id', '')
    tenant_id = getattr(item, 'tenant_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    available_ip_address_count = getattr(item, 'available_ip_address_count', '')
    output = f"id\tname\tdescription\tcidr\tgateway_ip\tipv6_enable\tcidr_v6\tgateway_ip_v6\tdhcp_enable\tprimary_dns\tsecondary_dns\tdns_list\tavailability_zone\tvpc_id\tstatus\tneutron_network_id\tneutron_subnet_id\ttenant_id\tcreated_at\tupdated_at\tavailable_ip_address_count\n"
    output += f"{id}\t{name}\t{description}\t{cidr}\t{gateway_ip}\t{ipv6_enable}\t{cidr_v6}\t{gateway_ip_v6}\t{dhcp_enable}\t{primary_dns}\t{secondary_dns}\t{dns_list}\t{availability_zone}\t{vpc_id}\t{status}\t{neutron_network_id}\t{neutron_subnet_id}\t{tenant_id}\t{created_at}\t{updated_at}\t{available_ip_address_count}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_subnet 查询失败: {e}")
    exit(1)
