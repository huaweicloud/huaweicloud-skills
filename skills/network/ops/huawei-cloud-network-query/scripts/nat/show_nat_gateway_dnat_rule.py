import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowNatGatewayDnatRuleRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网NAT网关DNAT规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--dnat_rule_id", type=str, required=True, help="DNAT 规则 ID（必填），可通过 list_nat_gateway_dnat_rules.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    request = ShowNatGatewayDnatRuleRequest()
    request.dnat_rule_id = args.dnat_rule_id
    response = client.show_nat_gateway_dnat_rule(request)
    item = response.dnat_rule
    if not item:
        print(f"没有找到 DNAT 规则")
        exit(0)

    id = getattr(item, 'id', '')
    nat_gateway_id = getattr(item, 'nat_gateway_id', '')
    protocol = getattr(item, 'protocol', '')
    floating_ip_address = getattr(item, 'floating_ip_address', '')
    floating_ip_id = getattr(item, 'floating_ip_id', '')
    external_service_port = getattr(item, 'external_service_port', '')
    internal_service_port = getattr(item, 'internal_service_port', '')
    private_ip = getattr(item, 'private_ip', '')
    port_id = getattr(item, 'port_id', '')
    status = getattr(item, 'status', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    description = getattr(item, 'description', '')
    created_at = getattr(item, 'created_at', '')
    global_eip_id = getattr(item, 'global_eip_id', '')
    global_eip_address = getattr(item, 'global_eip_address', '')
    internal_service_port_range = getattr(item, 'internal_service_port_range', '')
    external_service_port_range = getattr(item, 'external_service_port_range', '')
    output = f"id\tnat_gateway_id\tprotocol\tfloating_ip_address\tfloating_ip_id\texternal_service_port\tinternal_service_port\tprivate_ip\tport_id\tstatus\tadmin_state_up\tcreated_at\tglobal_eip_id\tglobal_eip_address\tinternal_service_port_range\texternal_service_port_range\tdescription\n"
    output += f"{id}\t{nat_gateway_id}\t{protocol}\t{floating_ip_address}\t{floating_ip_id}\t{external_service_port}\t{internal_service_port}\t{private_ip}\t{port_id}\t{status}\t{admin_state_up}\t{created_at}\t{global_eip_id}\t{global_eip_address}\t{internal_service_port_range}\t{external_service_port_range}\t{description}\n"
    print(output)
except Exception as e:
    print(f"nat.show_nat_gateway_dnat_rule 查询失败: {e}")
    exit(1)
