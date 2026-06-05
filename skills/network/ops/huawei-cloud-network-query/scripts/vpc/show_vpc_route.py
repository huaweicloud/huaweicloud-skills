import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowVpcRouteRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询VPC路由详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--route_id", type=str, required=True, help="VPC路由 ID（必填），可通过 list_vpc_routes.py 获取")
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

    request = ShowVpcRouteRequest()
    request.route_id = args.route_id
    response = client.show_vpc_route(request)
    item = response.route
    if not item:
        print(f"没有找到VPC路由")
        exit(0)

    id = getattr(item, 'id', '')
    destination = getattr(item, 'destination', '')
    nexthop = getattr(item, 'nexthop', '')
    route_type = getattr(item, 'type', '')
    vpc_id = getattr(item, 'vpc_id', '')
    tenant_id = getattr(item, 'tenant_id', '')
    output = f"id\tdestination\tnexthop\ttype\tvpc_id\ttenant_id\n"
    output += f"{id}\t{destination}\t{nexthop}\t{route_type}\t{vpc_id}\t{tenant_id}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_vpc_route 查询失败: {e}")
    exit(1)
