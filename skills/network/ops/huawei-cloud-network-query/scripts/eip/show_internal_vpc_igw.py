import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ShowInternalVpcIgwRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询虚拟IGW（Internet网关）详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--vpc_igw_id", type=str, required=True, help="虚拟IGW ID，可通过 list_tenant_vpc_igws.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EipClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EipRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EIP 客户端")
        exit(-1)

    request = ShowInternalVpcIgwRequest()
    request.vpc_igw_id = args.vpc_igw_id
    response = client.show_internal_vpc_igw(request)

    igw = response.vpc_igw
    if not igw:
        print(f"没有找到虚拟IGW (ID: {args.vpc_igw_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(igw, 'id', '')}\n"
    output += f"name: {getattr(igw, 'name', '')}\n"
    output += f"vpc_id: {getattr(igw, 'vpc_id', '')}\n"
    output += f"project_id: {getattr(igw, 'project_id', '')}\n"
    output += f"network_id: {getattr(igw, 'network_id', '')}\n"
    output += f"enable_ipv6: {getattr(igw, 'enable_ipv6', '')}\n"
    output += f"created_at: {getattr(igw, 'created_at', '')}\n"
    output += f"updated_at: {getattr(igw, 'updated_at', '')}\n"
    print(output)
except Exception as e:
    print(f"eip.show_internal_vpc_igw 查询失败: {e}")
    exit(1)
