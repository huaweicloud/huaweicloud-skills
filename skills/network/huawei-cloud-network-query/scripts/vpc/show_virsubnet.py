import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowVirsubnetRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询子网详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--virsubnet_id", type=str, required=True, help="子网 ID（必填），可通过 list_virsubnets.py 获取")
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

    request = ShowVirsubnetRequest()
    request.virsubnet_id = args.virsubnet_id
    response = client.show_virsubnet(request)
    item = response.virsubnet
    if not item:
        print(f"没有找到子网")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    dns_nameservers = getattr(item, 'dns_nameservers', [])
    zone_id = getattr(item, 'zone_id', '')
    vpc_id = getattr(item, 'vpc_id', '')
    status = getattr(item, 'status', '')
    project_id = getattr(item, 'project_id', '')
    scope = getattr(item, 'scope', '')
    subnet_cidrs = getattr(item, 'subnet_cidrs', [])
    tags = getattr(item, 'tags', [])
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tname\tdescription\tdns_nameservers\tzone_id\tvpc_id\tstatus\tproject_id\tscope\tsubnet_cidrs\ttags\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{description}\t{dns_nameservers}\t{zone_id}\t{vpc_id}\t{status}\t{project_id}\t{scope}\t{subnet_cidrs}\t{tags}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_virsubnet 查询失败: {e}")
    exit(1)
