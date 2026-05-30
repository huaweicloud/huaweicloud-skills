import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ShowPublicipPoolRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网IP池详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--publicip_pool_id", type=str, required=True, help="公网IP池 ID，可通过 list_publicip_pool.py 获取")
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

    request = ShowPublicipPoolRequest()
    request.publicip_pool_id = args.publicip_pool_id
    response = client.show_publicip_pool(request)

    pool = response.publicip_pool
    if not pool:
        print(f"没有找到公网IP池 (ID: {args.publicip_pool_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(pool, 'id', '')}\n"
    output += f"name: {getattr(pool, 'name', '')}\n"
    output += f"type: {getattr(pool, 'type', '')}\n"
    output += f"status: {getattr(pool, 'status', '')}\n"
    output += f"size: {getattr(pool, 'size', '')}\n"
    output += f"used: {getattr(pool, 'used', '')}\n"
    output += f"description: {getattr(pool, 'description', '')}\n"
    output += f"project_id: {getattr(pool, 'project_id', '')}\n"
    output += f"public_border_group: {getattr(pool, 'public_border_group', '')}\n"
    output += f"shared: {getattr(pool, 'shared', '')}\n"
    output += f"is_common: {getattr(pool, 'is_common', '')}\n"
    output += f"enterprise_project_id: {getattr(pool, 'enterprise_project_id', '')}\n"
    output += f"created_at: {getattr(pool, 'created_at', '')}\n"
    output += f"updated_at: {getattr(pool, 'updated_at', '')}\n"
    billing_info = getattr(pool, 'billing_info', None)
    if billing_info:
        output += f"billing_info.order_id: {getattr(billing_info, 'order_id', '')}\n"
        output += f"billing_info.product_id: {getattr(billing_info, 'product_id', '')}\n"
    print(output)
except Exception as e:
    print(f"eip.show_publicip_pool 查询失败: {e}")
    exit(1)
