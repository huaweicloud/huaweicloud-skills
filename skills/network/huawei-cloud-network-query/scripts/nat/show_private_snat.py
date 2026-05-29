import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowPrivateSnatRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询私网NAT网关SNAT规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--snat_rule_id", type=str, required=True, help="SNAT 规则 ID（必填），可通过 list_private_snats.py 获取")
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

    request = ShowPrivateSnatRequest()
    request.snat_rule_id = args.snat_rule_id
    response = client.show_private_snat(request)
    item = response.snat_rule
    if not item:
        print(f"没有找到私网 SNAT 规则")
        exit(0)

    id = getattr(item, 'id', '')
    gateway_id = getattr(item, 'gateway_id', '')
    cidr = getattr(item, 'cidr', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    description = getattr(item, 'description', '')
    status = getattr(item, 'status', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    transit_ip_associations = getattr(item, 'transit_ip_associations', [])
    transit_str = ';'.join([f"{getattr(a,'transit_ip_id','')}:{getattr(a,'transit_ip_address','')}" for a in transit_ip_associations]) if transit_ip_associations else ''
    output = f"id\tgateway_id\tcidr\tvirsubnet_id\ttransit_ip_associations\tenterprise_project_id\tstatus\tcreated_at\tupdated_at\tdescription\n"
    output += f"{id}\t{gateway_id}\t{cidr}\t{virsubnet_id}\t{transit_str}\t{enterprise_project_id}\t{status}\t{created_at}\t{updated_at}\t{description}\n"
    print(output)
except Exception as e:
    print(f"nat.show_private_snat 查询失败: {e}")
    exit(1)
