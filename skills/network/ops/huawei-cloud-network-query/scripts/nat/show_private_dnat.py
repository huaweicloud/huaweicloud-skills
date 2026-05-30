import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowPrivateDnatRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询私网NAT网关DNAT规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--dnat_rule_id", type=str, required=True, help="DNAT 规则 ID（必填），可通过 list_private_dnats.py 获取")
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

    request = ShowPrivateDnatRequest()
    request.dnat_rule_id = args.dnat_rule_id
    response = client.show_private_dnat(request)
    item = response.dnat_rule
    if not item:
        print(f"没有找到私网 DNAT 规则")
        exit(0)

    id = getattr(item, 'id', '')
    gateway_id = getattr(item, 'gateway_id', '')
    transit_ip_id = getattr(item, 'transit_ip_id', '')
    network_interface_id = getattr(item, 'network_interface_id', '')
    type_ = getattr(item, 'type', '')
    protocol = getattr(item, 'protocol', '')
    private_ip_address = getattr(item, 'private_ip_address', '')
    internal_service_port = getattr(item, 'internal_service_port', '')
    transit_service_port = getattr(item, 'transit_service_port', '')
    status = getattr(item, 'status', '')
    description = getattr(item, 'description', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tgateway_id\ttransit_ip_id\tnetwork_interface_id\ttype\tprotocol\tprivate_ip_address\tinternal_service_port\ttransit_service_port\tstatus\tdescription\tenterprise_project_id\tcreated_at\tupdated_at\n"
    output += f"{id}\t{gateway_id}\t{transit_ip_id}\t{network_interface_id}\t{type_}\t{protocol}\t{private_ip_address}\t{internal_service_port}\t{transit_service_port}\t{status}\t{description}\t{enterprise_project_id}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"nat.show_private_dnat 查询失败: {e}")
    exit(1)
