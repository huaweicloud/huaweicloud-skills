import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ShowPublicipPoolTypesRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询公网IP池类型列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--id", type=str, help="公网IP池类型 ID，精确匹配")
parser.add_argument("--name", type=str, help="公网IP池类型名称，精确匹配")
parser.add_argument("--type", type=str, help="公网IP池类型，如 bgp/sbgp 等")
parser.add_argument("--status", type=str, help="公网IP池类型状态")
parser.add_argument("--public_border_group", type=str, help="站点信息，可通过 list_common_pools.py 获取")
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

    request = ShowPublicipPoolTypesRequest()
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.type:
        request.type = args.type
    if args.status:
        request.status = args.status
    if args.public_border_group:
        request.public_border_group = args.public_border_group
    response = client.show_publicip_pool_types(request)

    pool_types = response.publicip_pool_types
    if not pool_types:
        print(f"没有找到公网IP池类型 (区域: {Region})")
        exit(0)

    # publicip_pool_types 是 PublicPoolType 单个对象（非列表）
    pt_id = getattr(pool_types, 'id', '')
    pt_type = getattr(pool_types, 'type', '')
    print(f"id: {pt_id}\ntype: {pt_type}")
except Exception as e:
    print(f"eip.show_publicip_pool_types 查询失败: {e}")
    exit(1)
