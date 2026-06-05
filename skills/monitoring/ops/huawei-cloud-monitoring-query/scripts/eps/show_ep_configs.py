import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowEpConfigsRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目服务配置")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    request = ShowEpConfigsRequest()
    response = client.show_ep_configs(request)

    support_item = getattr(response, 'support_item', None)
    if not support_item:
        print(f"没有找到企业项目服务配置")
        exit(0)

    # 输出所有属性
    output = ""
    for attr in dir(support_item):
        if attr.startswith('_'):
            continue
        val = getattr(support_item, attr)
        if callable(val):
            continue
        output += f"{attr}:\t{val}\n"
    print(output.strip())
except Exception as e:
    print(f"eps.show_ep_configs 查询失败: {e}")
    exit(1)
