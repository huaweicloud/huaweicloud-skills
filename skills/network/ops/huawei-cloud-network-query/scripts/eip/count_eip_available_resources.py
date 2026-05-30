import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import CountEipAvailableResourcesRequest, EipResourcesAvailableV3RequestBody
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询弹性公网IP可用资源数量")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--type", type=str, required=True, choices=["5_bgp", "5_sbgp", "5_telcom", "5_union", "5_ipv6", "5_graybgp"], help="公共池类型: 5_bgp(动态BGP)/5_sbgp(静态BGP)/5_telcom(联通)/5_union(联合)/5_ipv6(IPv6)/5_graybgp(灰度BGP)")
parser.add_argument("--limit", type=int, help="查询的公共池数量限制")
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

    body = EipResourcesAvailableV3RequestBody()
    body.type = args.type
    if args.limit is not None:
        body.limit = args.limit

    request = CountEipAvailableResourcesRequest()
    request.body = body
    response = client.count_eip_available_resources(request)

    result = response.result
    print(f"可用弹性公网IP数量: {result} (类型: {args.type}, 区域: {Region})")
except Exception as e:
    print(f"eip.count_eip_available_resources 查询失败: {e}")
    exit(1)
