import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowPrivateNatRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询私网NAT网关详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--gateway_id", type=str, required=True, help="私网 NAT 网关 ID（必填），可通过 list_private_nats.py 获取")
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

    request = ShowPrivateNatRequest()
    request.gateway_id = args.gateway_id
    response = client.show_private_nat(request)
    item = response.gateway
    if not item:
        print(f"没有找到私网 NAT 网关")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    spec = getattr(item, 'spec', '')
    status = getattr(item, 'status', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    rule_max = getattr(item, 'rule_max', '')
    transit_ip_pool_size_max = getattr(item, 'transit_ip_pool_size_max', '')
    downlink_vpcs = getattr(item, 'downlink_vpcs', [])
    vpc_str = ';'.join([f"{getattr(v,'vpc_id','')}({getattr(v,'virsubnet_id','')})" for v in downlink_vpcs]) if downlink_vpcs else ''
    tags = getattr(item, 'tags', [])
    tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in tags]) if tags else ''
    output = f"id\tname\tdescription\tspec\tstatus\tenterprise_project_id\tcreated_at\tupdated_at\trule_max\ttransit_ip_pool_size_max\tdownlink_vpcs\ttags\n"
    output += f"{id}\t{name}\t{description}\t{spec}\t{status}\t{enterprise_project_id}\t{created_at}\t{updated_at}\t{rule_max}\t{transit_ip_pool_size_max}\t{vpc_str}\t{tag_str}\n"
    print(output)
except Exception as e:
    print(f"nat.show_private_nat 查询失败: {e}")
    exit(1)
