import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowNatGatewayRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网NAT网关详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--nat_gateway_id", type=str, required=True, help="NAT 网关 ID（必填），可通过 list_nat_gateways.py 获取")
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

    request = ShowNatGatewayRequest()
    request.nat_gateway_id = args.nat_gateway_id
    response = client.show_nat_gateway(request)
    item = response.nat_gateway
    if not item:
        print(f"没有找到 NAT 网关")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    spec = getattr(item, 'spec', '')
    status = getattr(item, 'status', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    router_id = getattr(item, 'router_id', '')
    internal_network_id = getattr(item, 'internal_network_id', '')
    ngport_ip_address = getattr(item, 'ngport_ip_address', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    created_at = getattr(item, 'created_at', '')
    session_conf = getattr(item, 'session_conf', None)
    tcp_session_expire_time = getattr(session_conf, 'tcp_session_expire_time', '') if session_conf else ''
    udp_session_expire_time = getattr(session_conf, 'udp_session_expire_time', '') if session_conf else ''
    icmp_session_expire_time = getattr(session_conf, 'icmp_session_expire_time', '') if session_conf else ''
    tcp_time_wait_time = getattr(session_conf, 'tcp_time_wait_time', '') if session_conf else ''
    billing_info = getattr(item, 'billing_info', '')
    dnat_rules_limit = getattr(item, 'dnat_rules_limit', '')
    snat_rule_public_ip_limit = getattr(item, 'snat_rule_public_ip_limit', '')
    pps_max = getattr(item, 'pps_max', '')
    bps_max = getattr(item, 'bps_max', '')
    output = f"id\tname\tdescription\tspec\tstatus\tadmin_state_up\trouter_id\tinternal_network_id\tngport_ip_address\tenterprise_project_id\tcreated_at\tdnat_rules_limit\tsnat_rule_public_ip_limit\tpps_max\tbps_max\tbilling_info\ttcp_session_expire_time\tudp_session_expire_time\ticmp_session_expire_time\ttcp_time_wait_time\n"
    output += f"{id}\t{name}\t{description}\t{spec}\t{status}\t{admin_state_up}\t{router_id}\t{internal_network_id}\t{ngport_ip_address}\t{enterprise_project_id}\t{created_at}\t{dnat_rules_limit}\t{snat_rule_public_ip_limit}\t{pps_max}\t{bps_max}\t{billing_info}\t{tcp_session_expire_time}\t{udp_session_expire_time}\t{icmp_session_expire_time}\t{tcp_time_wait_time}\n"
    print(output)
except Exception as e:
    print(f"nat.show_nat_gateway 查询失败: {e}")
    exit(1)
