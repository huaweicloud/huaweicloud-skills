import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowRouteTableRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询路由表详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--routetable_id", type=str, required=True, help="路由表 ID（必填），可通过 list_route_tables.py 获取")
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

    request = ShowRouteTableRequest()
    request.routetable_id = args.routetable_id
    response = client.show_route_table(request)
    item = response.routetable
    if not item:
        print(f"没有找到路由表")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    default = getattr(item, 'default', '')
    routes = getattr(item, 'routes', [])
    subnets = getattr(item, 'subnets', [])
    tenant_id = getattr(item, 'tenant_id', '')
    vpc_id = getattr(item, 'vpc_id', '')
    description = getattr(item, 'description', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tname\tdefault\troutes\tsubnets\ttenant_id\tvpc_id\tdescription\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{default}\t{len(routes) if routes else 0}\t{len(subnets) if subnets else 0}\t{tenant_id}\t{vpc_id}\t{description}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_route_table 查询失败: {e}")
    exit(1)
