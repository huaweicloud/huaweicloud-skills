import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowVpcPeeringRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询VPC对等连接详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--peering_id", type=str, required=True, help="VPC对等连接 ID（必填），可通过 list_vpc_peerings.py 获取")
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

    request = ShowVpcPeeringRequest()
    request.peering_id = args.peering_id
    response = client.show_vpc_peering(request)
    item = response.peering
    if not item:
        print(f"没有找到VPC对等连接")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    status = getattr(item, 'status', '')
    request_vpc_info = getattr(item, 'request_vpc_info', None)
    accept_vpc_info = getattr(item, 'accept_vpc_info', None)
    description = getattr(item, 'description', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tname\tstatus\trequest_vpc_info\taccept_vpc_info\tdescription\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{status}\t{request_vpc_info}\t{accept_vpc_info}\t{description}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_vpc_peering 查询失败: {e}")
    exit(1)
