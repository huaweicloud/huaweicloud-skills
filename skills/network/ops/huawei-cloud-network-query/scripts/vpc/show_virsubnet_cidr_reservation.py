import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowVirsubnetCidrReservationRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询子网CIDR保留详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--virsubnet_cidr_reservation_id", type=str, required=True, help="子网CIDR保留 ID（必填），可通过 list_virsubnet_cidr_reservations.py 获取")
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

    request = ShowVirsubnetCidrReservationRequest()
    request.virsubnet_cidr_reservation_id = args.virsubnet_cidr_reservation_id
    response = client.show_virsubnet_cidr_reservation(request)
    item = response.virsubnet_cidr_reservation
    if not item:
        print(f"没有找到子网CIDR保留")
        exit(0)

    id = getattr(item, 'id', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    vpc_id = getattr(item, 'vpc_id', '')
    ip_version = getattr(item, 'ip_version', '')
    cidr = getattr(item, 'cidr', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    project_id = getattr(item, 'project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tvirsubnet_id\tvpc_id\tip_version\tcidr\tname\tdescription\tproject_id\tcreated_at\tupdated_at\n"
    output += f"{id}\t{virsubnet_id}\t{vpc_id}\t{ip_version}\t{cidr}\t{name}\t{description}\t{project_id}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_virsubnet_cidr_reservation 查询失败: {e}")
    exit(1)
