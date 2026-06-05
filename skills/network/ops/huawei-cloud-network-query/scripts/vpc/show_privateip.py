import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowPrivateipRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询私有IP详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--privateip_id", type=str, required=True, help="私有IP ID（必填），可通过 list_privateips.py 获取")
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

    request = ShowPrivateipRequest()
    request.privateip_id = args.privateip_id
    response = client.show_privateip(request)
    item = response.privateip
    if not item:
        print(f"没有找到私有IP")
        exit(0)

    id = getattr(item, 'id', '')
    subnet_id = getattr(item, 'subnet_id', '')
    tenant_id = getattr(item, 'tenant_id', '')
    ip_address = getattr(item, 'ip_address', '')
    status = getattr(item, 'status', '')
    device_owner = getattr(item, 'device_owner', '')
    output = f"id\tsubnet_id\ttenant_id\tip_address\tstatus\tdevice_owner\n"
    output += f"{id}\t{subnet_id}\t{tenant_id}\t{ip_address}\t{status}\t{device_owner}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_privateip 查询失败: {e}")
    exit(1)
