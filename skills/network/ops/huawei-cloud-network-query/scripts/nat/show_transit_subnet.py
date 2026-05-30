import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowTransitSubnetRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询中转子网详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--transit_subnet_id", type=str, required=True, help="中转子网 ID（必填），可通过 list_transit_subnet.py 获取")
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

    request = ShowTransitSubnetRequest()
    request.transit_subnet_id = args.transit_subnet_id
    response = client.show_transit_subnet(request)
    item = response.transit_subnet
    if not item:
        print(f"没有找到中转子网")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    vpc_id = getattr(item, 'vpc_id', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    cidr = getattr(item, 'cidr', '')
    type_ = getattr(item, 'type', '')
    status = getattr(item, 'status', '')
    ip_count = getattr(item, 'ip_count', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    virsubnet_project_id = getattr(item, 'virsubnet_project_id', '')
    tags = getattr(item, 'tags', [])
    tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in tags]) if tags else ''
    output = f"id\tname\tdescription\tvpc_id\tvirsubnet_id\tcidr\ttype\tstatus\tip_count\tvirsubnet_project_id\tcreated_at\tupdated_at\ttags\n"
    output += f"{id}\t{name}\t{description}\t{vpc_id}\t{virsubnet_id}\t{cidr}\t{type_}\t{status}\t{ip_count}\t{virsubnet_project_id}\t{created_at}\t{updated_at}\t{tag_str}\n"
    print(output)
except Exception as e:
    print(f"nat.show_transit_subnet 查询失败: {e}")
    exit(1)
