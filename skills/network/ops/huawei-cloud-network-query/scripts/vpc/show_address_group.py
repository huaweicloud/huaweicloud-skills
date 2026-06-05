import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowAddressGroupRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询地址组详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--address_group_id", type=str, required=True, help="地址组 ID（必填），可通过 list_address_group.py 获取")
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

    request = ShowAddressGroupRequest()
    request.address_group_id = args.address_group_id
    response = client.show_address_group(request)
    item = response.address_group
    if not item:
        print(f"没有找到地址组")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    max_capacity = getattr(item, 'max_capacity', '')
    ip_set = getattr(item, 'ip_set', [])
    ip_version = getattr(item, 'ip_version', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    tenant_id = getattr(item, 'tenant_id', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tags = getattr(item, 'tags', [])
    status = getattr(item, 'status', '')
    status_message = getattr(item, 'status_message', '')
    output = f"id\tname\tdescription\tmax_capacity\tip_set\tip_version\tcreated_at\tupdated_at\ttenant_id\tenterprise_project_id\ttags\tstatus\tstatus_message\n"
    output += f"{id}\t{name}\t{description}\t{max_capacity}\t{','.join(str(i) for i in ip_set) if ip_set else ''}\t{ip_version}\t{created_at}\t{updated_at}\t{tenant_id}\t{enterprise_project_id}\t{tags}\t{status}\t{status_message}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_address_group 查询失败: {e}")
    exit(1)
