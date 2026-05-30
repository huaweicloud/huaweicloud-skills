import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowLoadBalancerRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 负载均衡器详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--loadbalancer_id", type=str, required=True, help="负载均衡器ID，可通过 list_load_balancers.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowLoadBalancerRequest()
    request.loadbalancer_id = args.loadbalancer_id
    response = client.show_load_balancer(request)
    item = response.loadbalancer
    if not item:
        print(f"没有找到负载均衡器")
        exit(0)

    # 输出详情
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    vip_address = getattr(item, 'vip_address', '')
    provisioning_status = getattr(item, 'provisioning_status', '')
    operating_status = getattr(item, 'operating_status', '')
    vpc_id = getattr(item, 'vpc_id', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    guaranteed = getattr(item, 'guaranteed', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    availability_zone_list = getattr(item, 'availability_zone_list', [])
    availability_zones = ','.join(availability_zone_list) if availability_zone_list else ''
    charge_mode = getattr(item, 'charge_mode', '')
    l4_flavor_id = getattr(item, 'l4_flavor_id', '')
    l7_flavor_id = getattr(item, 'l7_flavor_id', '')
    ip_target_enable = getattr(item, 'ip_target_enable', '')
    deletion_protection_enable = getattr(item, 'deletion_protection_enable', '')
    # 获取公网IP
    publicips = getattr(item, 'publicips', None)
    if publicips:
        public_ip = ','.join([getattr(p, 'publicip_address', '') for p in publicips if getattr(p, 'publicip_address', '')])
    else:
        eips = getattr(item, 'eips', None)
        if eips:
            public_ip = ','.join([getattr(e, 'eip_address', '') for e in eips if getattr(e, 'eip_address', '')])
        else:
            public_ip = ''
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id: {id}\n"
    output += f"name: {name}\n"
    output += f"description: {description}\n"
    output += f"vip_address: {vip_address}\n"
    output += f"public_ip: {public_ip}\n"
    output += f"provisioning_status: {provisioning_status}\n"
    output += f"operating_status: {operating_status}\n"
    output += f"vpc_id: {vpc_id}\n"
    output += f"admin_state_up: {admin_state_up}\n"
    output += f"guaranteed: {guaranteed}\n"
    output += f"enterprise_project_id: {enterprise_project_id}\n"
    output += f"availability_zones: {availability_zones}\n"
    output += f"charge_mode: {charge_mode}\n"
    output += f"l4_flavor_id: {l4_flavor_id}\n"
    output += f"l7_flavor_id: {l7_flavor_id}\n"
    output += f"ip_target_enable: {ip_target_enable}\n"
    output += f"deletion_protection_enable: {deletion_protection_enable}\n"
    output += f"created_at: {created_at}\n"
    output += f"updated_at: {updated_at}\n"
    print(output)
except Exception as e:
    print(f"elb.show_load_balancer 查询失败: {e}")
    exit(1)
