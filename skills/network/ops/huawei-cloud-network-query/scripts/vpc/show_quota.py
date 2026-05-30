import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowQuotaRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
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

    request = ShowQuotaRequest()
    response = client.show_quota(request)
    quota = response.quota
    if not quota:
        print(f"没有找到配额信息")
        exit(0)

    # quota 是 VpcQuotas 对象，所有属性为 int 类型
    output = "key\tvalue\n"
    for attr in sorted(quota.openapi_types.keys()) if hasattr(quota, 'openapi_types') else []:
        val = getattr(quota, attr, None)
        if val is not None:
            output += f"{attr}\t{val}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_quota 查询失败: {e}")
    exit(1)
